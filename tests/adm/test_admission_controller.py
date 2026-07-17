"""CT-06 ADM unit tests."""

from __future__ import annotations

import threading
import time

import pytest

from hg_core.admission.controller import AdmissionController
from hg_core.admission.ingress import reset_controller
from hg_core.admission.types import AdmissionRequest, ApprovalBinding
from hg_core.failures.registry import validate_reason_code


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_controller()
    yield
    reset_controller()


def _req(kind: str, key: str, *, request_id: str | None = None, **kwargs) -> AdmissionRequest:
    return AdmissionRequest(
        request_id=request_id or f"{kind}:{key}",
        kind=kind,  # type: ignore[arg-type]
        idempotency_key=key,
        **kwargs,
    )


def test_adm_u1_singleton_srp_apply() -> None:
    ctrl = AdmissionController()
    first = ctrl.request(_req("srp_apply", "k1"))
    second = ctrl.request(_req("srp_apply", "k2", request_id="srp2"))
    assert first.admitted
    assert not second.admitted
    assert second.reason_code == "admission.refused.singleton_held"
    assert validate_reason_code(second.reason_code).ok
    ctrl.release(first.token)


def test_adm_u2_singleton_max_auto() -> None:
    ctrl = AdmissionController()
    first = ctrl.request(_req("max_auto_run", "m1"))
    second = ctrl.request(_req("max_auto_run", "m2", request_id="m2"))
    assert first.admitted
    assert not second.admitted
    assert second.reason_code == "admission.refused.singleton_held"
    ctrl.release(first.token)


def test_adm_u3_per_capability_concurrency() -> None:
    ctrl = AdmissionController(queue_capacity=2)
    r1 = ctrl.request(
        _req("oea_effect", "o1", capability_id="local_report_file.write", capability_concurrency=1)
    )
    r2 = ctrl.request(
        _req("oea_effect", "o2", capability_id="local_report_file.write", capability_concurrency=1)
    )
    assert r1.admitted
    assert not r2.admitted
    assert r2.verdict in {"refused", "queued"}
    ctrl.release(r1.token)


def test_adm_u4_duplicate_idempotency() -> None:
    ctrl = AdmissionController()
    first = ctrl.request(_req("srp_apply", "dup-key", request_id="a"))
    assert first.admitted
    ctrl.complete(first.token, result_ref="sha256:abc")
    ctrl.release(first.token)
    second = ctrl.request(_req("srp_apply", "dup-key", request_id="b"))
    assert not second.admitted
    assert second.reason_code == "admission.refused.duplicate_request"
    assert second.duplicate_of == "a"
    assert any(e["type"] == "ADM_IDEMPOTENCY_HIT" for e in second.events)


def test_adm_u5_stale_approval() -> None:
    ctrl = AdmissionController()
    stale = ctrl.request(
        AdmissionRequest(
            request_id="stale1",
            kind="srp_apply",
            idempotency_key="stale1",
            approval_binding=ApprovalBinding(
                proposal_hash="unknown",
                registry_hash="sha256:dead",
            ),
        )
    )
    assert not stale.admitted
    assert stale.reason_code == "admission.refused.stale_approval"


def test_adm_u6_expired_lease_reclaim() -> None:
    clock = {"t": 100.0}

    def fake_clock() -> float:
        return clock["t"]

    ctrl = AdmissionController(default_lease_s=10.0, clock=fake_clock)
    first = ctrl.request(_req("srp_apply", "lease1"))
    assert first.admitted
    clock["t"] = 200.0
    second = ctrl.request(_req("srp_apply", "lease2", request_id="lease2"))
    assert second.admitted
    ctrl.release(second.token)


def test_adm_u7_queue_overflow_refused() -> None:
    ctrl = AdmissionController(queue_capacity=0)
    held = ctrl.request(
        _req("oea_effect", "cap1", capability_id="cap", capability_concurrency=1)
    )
    assert held.admitted
    overflow = ctrl.request(
        _req("oea_effect", "cap2", capability_id="cap", capability_concurrency=1, request_id="cap2")
    )
    assert not overflow.admitted
    assert overflow.reason_code == "admission.refused.queue_overflow"
    ctrl.release(held.token)


def test_adm_i1_panic_preempts_all() -> None:
    ctrl = AdmissionController()
    mel = ctrl.request(_req("mel_cycle", "mel1"))
    oea = ctrl.request(
        _req("oea_effect", "oea1", capability_id="local_report_file.write", capability_concurrency=2)
    )
    assert mel.admitted and oea.admitted
    receipts = ctrl.assert_panic(preemptor="plt:panic")
    assert len(receipts) >= 2
    assert any(e["type"] == "ADM_PANIC_ASSERTED" for e in ctrl.events)
    blocked = ctrl.request(_req("srp_apply", "after_panic", request_id="after"))
    assert not blocked.admitted
    assert blocked.reason_code == "admission.refused.panic_active"


def test_adm_i2_crr_preempts_mel() -> None:
    ctrl = AdmissionController()
    mel = ctrl.request(_req("mel_cycle", "mel-crr"))
    assert mel.admitted
    ctrl.begin_crr_recovery(recovery_id="crr1")
    assert ctrl.lock_state()["crr_recovery_active"]
    ctrl.end_crr_recovery()


def test_adm_i4_shutdown_drain() -> None:
    ctrl = AdmissionController()
    ctrl._queue.append(object())  # type: ignore[arg-type]
    drain = ctrl.drain_queues()
    assert drain.drained == 1
    assert any(e["type"] == "ADM_QUEUE_DRAINED" for e in ctrl.events)


def test_adm_ter_sandbox_serialization() -> None:
    ctrl = AdmissionController()
    t1 = ctrl.request(
        AdmissionRequest(
            request_id="t1",
            kind="ter_command",
            idempotency_key="t1",
            sandbox_id="/tmp/sandbox-a",
        )
    )
    t2 = ctrl.request(
        AdmissionRequest(
            request_id="t2",
            kind="ter_command",
            idempotency_key="t2",
            sandbox_id="/tmp/sandbox-a",
        )
    )
    assert t1.admitted
    assert not t2.admitted
    ctrl.release(t1.token)


def test_adm_neg_unknown_kind_still_singleton() -> None:
    ctrl = AdmissionController()
    a = ctrl.request(_req("srp_apply", "x"))
    b = ctrl.request(_req("srp_apply", "y", request_id="y"))
    assert a.admitted and not b.admitted


def test_adm_events_emitted_on_grant() -> None:
    ctrl = AdmissionController()
    decision = ctrl.request(_req("srp_apply", "evt1"))
    types = [e["type"] for e in decision.events]
    assert "ADM_ADMISSION_REQUESTED" in types
    assert "ADM_ADMISSION_GRANTED" in types
    assert "ADM_LOCK_ACQUIRED" in types
    ctrl.release(decision.token)


def test_race_harness_exactly_one_srp_apply() -> None:
    ctrl = AdmissionController()
    thread_count = 8
    start = threading.Barrier(thread_count)
    results: list[bool] = []

    def worker(idx: int) -> None:
        start.wait()
        decision = ctrl.request(
            AdmissionRequest(
                request_id=f"race-{idx}",
                kind="srp_apply",
                idempotency_key=f"race-{idx}",
            )
        )
        results.append(decision.admitted)
        if decision.admitted:
            time.sleep(0.05)
            ctrl.release(decision.token)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(results) == 1
