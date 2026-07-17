"""GPP Phase 1 — permit binder scaffold tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.governance.permit_binder import PermitBinder, descriptor_for
from hg_core.governance.rtc_bridge import emit_bind_result
from hg_core.governance.trace_emitter import TraceEmitter
from hg_core.governance.types import BindRequest, permit_body_hash
from hg_runtime.bus import EventBus
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T09:00:{counter['value']:02d}.000000Z"

    return tick


def _binder(tmp_path: Path) -> PermitBinder:
    trace = TraceEmitter(tmp_path / "gpp" / "governance_trace.jsonl", enabled=True, clock=_clock())
    return PermitBinder(trace_emitter=trace, clock=_clock())


def _request(**overrides) -> BindRequest:
    payload = {
        "request_id": "req_1",
        "capability_id": "cap.oea_stub_log",
        "effect_class": "audit_log",
        "decision_ref": "dec_allow_stub",
    }
    payload.update(overrides)
    return BindRequest(**payload)


def test_canonical_permit_hash_is_deterministic(tmp_path: Path):
    binder = _binder(tmp_path)
    descriptor = descriptor_for("cap.oea_stub_log")
    first = binder.bind(_request(), descriptor)
    second = binder.bind(_request(request_id="req_2"), descriptor)

    assert first.permit is not None and second.permit is not None
    assert first.permit.permit_hash == permit_body_hash(first.permit.to_payload(include_hash=False))
    assert first.permit.permit_hash != second.permit.permit_hash


def test_same_input_produces_same_permit_hash(tmp_path: Path):
    binder = _binder(tmp_path)
    descriptor = descriptor_for("cap.oea_stub_log")

    fixed = PermitBinder(
        trace_emitter=TraceEmitter(
            tmp_path / "gpp" / "trace_a.jsonl", enabled=True, clock=_clock()
        ),
        clock=_clock(),
    )
    # Deterministic hash for permit body fields — permit_id differs per bind by design.
    request = _request()
    first = fixed.bind(request, descriptor)
    second = fixed.bind(_request(request_id="req_copy"), descriptor)

    assert first.permit is not None and second.permit is not None
    first_body = first.permit.to_payload(include_hash=False)
    second_body = second.permit.to_payload(include_hash=False)
    for body in (first_body, second_body):
        body["permit_id"] = "fixed"
        body["request_id"] = "req_fixed"
        body["issued_at"] = "2026-06-11T09:00:01.000000Z"
        body["trace_ref"] = {
            "trace_path": "/tmp/trace.jsonl",
            "trace_seq": 1,
            "trace_event_hash": "sha256:" + "a" * 64,
        }
    assert permit_body_hash(first_body) == permit_body_hash(second_body)


def test_changed_capability_or_effect_changes_hash(tmp_path: Path):
    binder = _binder(tmp_path)
    allow = binder.bind(_request(), descriptor_for("cap.oea_stub_log"))
    memory = binder.bind(
        _request(
            request_id="req_mem",
            capability_id="cap.memory_write_stub",
            effect_class="derived_store",
        ),
        descriptor_for("cap.memory_write_stub"),
    )

    assert allow.permit is not None and memory.permit is not None
    assert allow.permit.permit_hash != memory.permit.permit_hash


def test_denied_bind_emits_reason_code(tmp_path: Path):
    binder = _binder(tmp_path)
    result = binder.bind(
        _request(decision_ref="dec_deny_policy"),
        descriptor_for("cap.oea_stub_log"),
    )

    assert result.outcome == "deny"
    assert result.deny is not None
    assert result.deny.reason_code == "policy_denied"


def test_permit_bind_emits_rtc_event_references(tmp_path: Path):
    binder = _binder(tmp_path)
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    result = binder.bind(_request(), descriptor_for("cap.oea_stub_log"))
    events = emit_bind_result(bus, result)

    types = [event["type"] for event in events]
    assert types == ["GPP_TRACE_RECORDED", "GPP_PERMIT_BOUND"]
    assert events[0]["payload"]["trace_event_hash"]
    assert events[1]["payload"]["permit_hash"]
    assert list(events[1]["causal_parents"]) == [events[0]["event_id"]]
    assert replay(tmp_path / "runtime").ok is True


def test_denied_bind_emits_gpp_bind_denied_rtc_event(tmp_path: Path):
    binder = _binder(tmp_path)
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    result = binder.bind(
        _request(decision_ref="dec_deny_policy"),
        descriptor_for("cap.oea_stub_log"),
    )
    events = emit_bind_result(bus, result)

    assert [event["type"] for event in events] == ["GPP_TRACE_RECORDED", "GPP_BIND_DENIED"]
    assert events[1]["payload"]["reason_code"] == "policy_denied"


def test_no_external_side_effects_in_gpp_scaffold_modules():
    forbidden = ("requests.", "httpx.", "urllib.", "subprocess.", "socket.", "hg_oea", "hg_ueak")
    targets = [
        Path("hg_core/governance/permit_binder.py"),
        Path("hg_core/governance/capability_registry.py"),
        Path("hg_core/governance/types.py"),
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_gpp_core_modules_do_not_bypass_rtc_bus_except_bridge():
    forbidden = ("bus.emit(", "EventBus(")
    for path in Path("hg_core/governance").glob("*.py"):
        if path.name in {"rtc_bridge.py", "__init__.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not bypass RTC bus via {token}"


def test_disallowed_capability_denied_without_permit(tmp_path: Path):
    binder = _binder(tmp_path)
    result = binder.bind(
        _request(
            request_id="req_ext",
            capability_id="cap.external_post",
            effect_class="external_write",
            decision_ref="dec_allow_stub",
        ),
        descriptor_for("cap.external_post"),
    )

    assert result.outcome == "deny"
    assert result.permit is None
    assert result.deny is not None
    assert result.deny.reason_code == "capability_denied"
