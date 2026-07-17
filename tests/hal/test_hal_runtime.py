"""HAL event-sourced runtime tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.governance.canonical_hash import canonical_hash
from hg_hal import (
    HalRuntime,
    fixture_hal_request,
    verify_replay,
)
from hg_hal.events import (
    HAL_DEGRADED_MODE_ENTERED,
    HAL_FAILED_CLOSED,
    HAL_GPP_ROUTE_REQUESTED,
    HAL_PANIC_ENTERED,
    HAL_ROUTE_SELECTED,
)
from hg_hal.models import HalEvent
from hg_hal.types import ArbitrationCandidate
from hg_hal.validation import (
    DENIED_DUPLICATE,
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_FRESHNESS,
    DENIED_MISSING_IDENTITY,
    DENIED_STALE_APPROVAL,
)


def _clock() -> str:
    return "2026-06-12T14:00:00.000000Z"


def _runtime() -> HalRuntime:
    return HalRuntime(clock=_clock)


def test_hal_event_schema_validation():
    event = HalEvent(
        seq=1,
        event_type="HAL_REQUEST_RECEIVED",
        timestamp=_clock(),
        request_id="req_1",
        payload={"request_id": "req_1"},
    )
    payload = event.to_payload()
    assert payload["schema"] == "hal-event"
    assert payload["event_type"] == "HAL_REQUEST_RECEIVED"
    assert payload["event_hash"] == canonical_hash(
        {
            "schema": "hal-event",
            "schema_version": "1.0",
            "seq": 1,
            "event_type": "HAL_REQUEST_RECEIVED",
            "timestamp": _clock(),
            "request_id": "req_1",
            "payload": {"request_id": "req_1"},
        }
    )


def test_stable_decision_hash():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_hal_request())
    expected = canonical_hash(decision.to_payload(include_hash=False))
    assert decision.decision_hash == expected


def test_replay_determinism():
    request = fixture_hal_request(request_id="hal_replay")
    first = _runtime()
    second = _runtime()
    d1, _ = first.process(request)
    d2, _ = second.process(request)
    assert d1.decision_hash == d2.decision_hash
    assert d1.decision_id == d2.decision_id


def test_event_ordering_monotonic():
    runtime = _runtime()
    _, events = runtime.process(fixture_hal_request())
    seqs = [event.seq for event in events]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))


def test_idempotency_duplicate_request():
    runtime = _runtime()
    request = fixture_hal_request(idempotency_key="idem_1")
    runtime.process(request)
    decision, events = runtime.process(request)
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_DUPLICATE for r in decision.reasons)
    assert any(event.event_type == HAL_FAILED_CLOSED for event in events)


def test_valid_route_to_gpp():
    runtime = _runtime()
    decision, events = runtime.process(fixture_hal_request())
    assert decision.decision_state == "route_to_GPP"
    assert decision.route.target == "GPP"
    types = [event.event_type for event in events]
    assert HAL_GPP_ROUTE_REQUESTED in types
    assert "permit_id" not in decision.to_payload()


def test_valid_route_to_operator_in_degraded_mode():
    runtime = _runtime()
    runtime.enter_degraded(mode="operator_only")
    decision, events = runtime.process(fixture_hal_request())
    assert decision.decision_state == "route_to_operator"
    assert decision.route.target == "operator"
    assert any(event.event_type == HAL_DEGRADED_MODE_ENTERED for event in runtime.log.events)


def test_missing_admission_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_hal_request(admission_ref="adm:missing"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_ADMISSION for r in decision.reasons)


def test_missing_freshness_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_hal_request(freshness_ref="tim:missing"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_FRESHNESS for r in decision.reasons)


def test_stale_approval_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(
        fixture_hal_request(approval_expires_at="2020-01-01T00:00:00.000000Z")
    )
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_STALE_APPROVAL for r in decision.reasons)


def test_missing_identity_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_hal_request(identity_ref="placeholder"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_IDENTITY for r in decision.reasons)


def test_secret_redaction_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(
        fixture_hal_request(
            redaction_ref="sec:redaction_failed",
            redaction_payload={"api_key": "sk-live-secret-token-abcdefghij"},
        )
    )
    assert decision.decision_state == "fail_closed"
    assert any("redaction" in r.code for r in decision.reasons)


def test_panic_state_blocks_routing():
    runtime = _runtime()
    runtime.enter_panic(reason_code="test_panic")
    decision, events = runtime.process(fixture_hal_request())
    assert decision.decision_state == "fail_closed"
    assert any(event.event_type == HAL_PANIC_ENTERED for event in runtime.log.events)
    assert not any(event.event_type == HAL_GPP_ROUTE_REQUESTED for event in events)


def test_degraded_mode_explicit():
    runtime = _runtime()
    event = runtime.enter_degraded(mode="operator_only")
    assert runtime.state.degraded.active is True
    assert runtime.state.degraded.mode == "operator_only"
    assert event.event_type == HAL_DEGRADED_MODE_ENTERED


def test_contradictory_inputs_preserved():
    runtime = _runtime()
    decision, events = runtime.process(
        fixture_hal_request(contradictions=("ctx:a", "ctx:b_conflict"))
    )
    route_event = next(event for event in events if event.event_type == HAL_ROUTE_SELECTED)
    assert route_event.payload["contradictions"] == ["ctx:a", "ctx:b_conflict"]
    assert list(decision.contradictions) == ["ctx:a", "ctx:b_conflict"]


def test_no_permit_minting():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_hal_request())
    forbidden = {"permit_id", "permit_ref", "permit_hash", "grant", "allow_permit"}
    assert forbidden.isdisjoint(decision.to_payload().keys())


def test_no_ueak_approval_in_decision():
    runtime = _runtime()
    decision, events = runtime.process(fixture_hal_request())
    assert decision.decision_state != "route_to_UEAK"
    assert decision.route.target != "UEAK"
    types = [event.event_type for event in events]
    assert "HAL_UEAK_ROUTE_REQUESTED" not in types or all(
        event.event_type != "HAL_UEAK_ROUTE_REQUESTED" for event in events
    )


def test_no_oea_ter_calls_in_hg_hal():
    forbidden = ("hg_oea", "hg_ter", "hg_ueak", "requests.", "httpx.", "subprocess.", "mint_permit")
    for path in Path("hg_hal").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_no_execution_side_effect():
    runtime = _runtime()
    runtime.process(fixture_hal_request())
    assert runtime.execution_log == []


def test_replay_verifier_matches_state():
    runtime = _runtime()
    runtime.process(fixture_hal_request())
    ok, reason = verify_replay(runtime.log, expected_state=runtime.state)
    assert ok, reason
    ok2, reason2 = runtime.verify_replay()
    assert ok2, reason2


def test_capability_denied_reject():
    runtime = _runtime()
    request = fixture_hal_request(
        candidates=(
            ArbitrationCandidate(
                candidate_id="cand_x",
                action_ref="act_x",
                capability_id="cap.external_post",
                effect_class="external_write",
            ),
        ),
    )
    decision, _ = runtime.process(request)
    assert decision.decision_state in {"reject", "request_clarification", "fail_closed"}
