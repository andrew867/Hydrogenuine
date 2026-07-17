from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from hg_aep import AEPSignal, build_arousal_state, emit_signal_event
from hg_aep.emitters.registry import EMITTERS, validate_emitter
from hg_aep.types import SignalValidationError
from hg_runtime.bus import EventBus
from hg_runtime.replay import replay


NOW = "2026-06-11T00:00:00.000000Z"


def _signal(**overrides) -> AEPSignal:
    payload = {
        "signal_id": "aep_test_1",
        "signal_class": "RESOURCE_PRESSURE",
        "severity": 7,
        "scope": "global",
        "source": {"component": "platform.health", "ref": "health:1"},
        "evidence_refs": ("health:1",),
        "emitted_at": NOW,
        "causal_parents": ("evt_parent",),
    }
    payload.update(overrides)
    return AEPSignal(**payload)


def test_signal_schema_has_no_authority_fields():
    schema = json.loads(Path("docs/schemas/aep_signal_v1.json").read_text(encoding="utf-8"))
    forbidden = {"grant", "permit", "allow", "deny", "approve", "reject", "verdict", "decision"}

    assert schema["additionalProperties"] is False
    assert forbidden.isdisjoint(schema["properties"])


def test_signal_validates_and_hashes_deterministically():
    first = _signal()
    second = _signal()

    assert first.signal_hash == second.signal_hash
    validate(
        instance=first.to_payload(),
        schema=json.loads(Path("docs/schemas/aep_signal_v1.json").read_text(encoding="utf-8")),
    )


def test_authority_bearing_signal_content_is_rejected():
    with pytest.raises(SignalValidationError):
        _signal(source={"component": "platform.health", "permit": "perm_123"})


def test_unknown_class_and_out_of_range_severity_rejected():
    with pytest.raises(SignalValidationError):
        _signal(signal_class="APPROVAL")
    with pytest.raises(SignalValidationError):
        _signal(severity=11)


def test_registered_emitters_are_class_limited_and_adapter_only():
    assert validate_emitter("platform.health", "RESOURCE_PRESSURE").detector_refs
    with pytest.raises(ValueError):
        validate_emitter("platform.health", "RISK")
    assert all(registration.detector_refs for registration in EMITTERS.values())


def test_arousal_state_uses_max_not_sum_and_scope_inheritance():
    signals = [
        _signal(signal_id=f"aep_low_{idx}", severity=3, scope="global")
        for idx in range(100)
    ]
    signals.append(
        _signal(
            signal_id="aep_request",
            signal_class="UNCERTAINTY",
            severity=6,
            scope="request:req1",
            source={"component": "platform.observations"},
        )
    )

    global_state = build_arousal_state(signals, scope="global", computed_at=NOW)
    request_state = build_arousal_state(signals, scope="request:req1", computed_at=NOW)

    assert global_state.levels["RESOURCE_PRESSURE"] == 3
    assert request_state.levels["RESOURCE_PRESSURE"] == 3
    assert request_state.levels["UNCERTAINTY"] == 6
    assert global_state.levels["UNCERTAINTY"] == 0


def test_signal_has_no_decision_or_permit_fields_in_payload():
    signal = _signal()
    payload = signal.to_payload()
    forbidden = {"grant", "permit", "allow", "deny", "approve", "reject", "verdict", "decision"}
    assert forbidden.isdisjoint(payload)
    assert forbidden.isdisjoint(payload.get("source", {}))


def test_aep_signal_emits_through_rtc_event_bus_and_replays(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    event = emit_signal_event(bus, _signal())

    assert event["type"] == "AEP_SIGNAL_EMITTED"
    assert event["payload"]["class"] == "RESOURCE_PRESSURE"
    assert bus.verify_chain()["ok"] is True
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["aep"]["signals"] == 1
    assert result.state["environment"]["arousal"]["max_severity"] == 7
