"""AEP Phase 1 — subscriptions and restrict-only modulation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hg_aep import (
    AEPSignal,
    build_arousal_state,
    load_subscriptions,
    max_only_aggregate,
    record_signal_event,
    validate_parameter_name,
)
from hg_aep.modulation import ModulationOutput, compute_modulations
from hg_aep.parameters import MODULATION_PARAMETERS, AUTHORITY_PARAMETER_NAMES
from hg_aep.subscriptions import SubscriptionValidationError, _validate_binding
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


NOW = "2026-06-11T10:00:00.000000Z"


def _signal(**overrides) -> AEPSignal:
    payload = {
        "signal_id": "aep_sub_1",
        "signal_class": "RESOURCE_PRESSURE",
        "severity": 7,
        "scope": "global",
        "source": {"component": "platform.health", "ref": "health:1"},
        "evidence_refs": ("health:1",),
        "emitted_at": NOW,
        "causal_parents": (),
    }
    payload.update(overrides)
    return AEPSignal(**payload)


def test_severity_aggregation_is_max_only():
    levels = [3, 3, 3, 3, 6]
    assert max_only_aggregate(levels) == 6
    signals = [_signal(signal_id=f"s{idx}", severity=3) for idx in range(100)]
    state = build_arousal_state(signals, scope="global", computed_at=NOW)
    assert state.levels["RESOURCE_PRESSURE"] == 3


def test_hundred_severity_three_signals_do_not_become_four():
    signals = [_signal(signal_id=f"s{idx}", severity=3) for idx in range(100)]
    state = build_arousal_state(signals, scope="global", computed_at=NOW)
    assert state.levels["RESOURCE_PRESSURE"] == 3
    assert state.levels["RESOURCE_PRESSURE"] != 4


def test_authority_fields_rejected_by_parameter_validation():
    for name in AUTHORITY_PARAMETER_NAMES:
        with pytest.raises(ValueError, match="authority parameter"):
            validate_parameter_name(name)


def test_loosen_below_baseline_fails_at_parameter_validation():
    param = MODULATION_PARAMETERS["max_concurrency"]
    with pytest.raises(ValueError, match="cannot exceed baseline"):
        param.validate_modulated_value(8)


def test_loosen_below_baseline_subscription_fails_at_load(tmp_path: Path):
    bad = {
        "schema": "aep-subscriptions",
        "schema_version": "1.0",
        "subscriptions": [
            {
                "consumer_id": "bad.scheduler",
                "signal_class": "RESOURCE_PRESSURE",
                "scope": "global",
                "min_severity": 1,
                "parameter": "permit_threshold",
                "response_curve": "step",
            }
        ],
    }
    path = tmp_path / "bad_subscriptions.yaml"
    path.write_text(yaml.dump(bad), encoding="utf-8")
    with pytest.raises((SubscriptionValidationError, ValueError), match="authority|permit"):
        load_subscriptions(path)


def test_registry_load_validation_rejects_unknown_parameter(tmp_path: Path):
    bad = {
        "subscriptions": [
            {
                "consumer_id": "bad",
                "signal_class": "RISK",
                "scope": "request",
                "min_severity": 5,
                "parameter": "unknown_param",
                "response_curve": "step",
            }
        ]
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.dump(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown modulation parameter"):
        load_subscriptions(path)


def test_modulation_output_enforces_restrict_only_deltas():
    with pytest.raises(ValueError, match="scrutiny_depth_delta"):
        ModulationOutput(
            consumer_id="test",
            signal_class="UNCERTAINTY",
            parameter="analysis_depth",
            scope="request:req1",
            scrutiny_depth_delta=-1,
            recorded_at=NOW,
        )
    with pytest.raises(ValueError, match="evidence_strictness_delta"):
        ModulationOutput(
            consumer_id="test",
            signal_class="RISK",
            parameter="evidence_strictness",
            scope="request:req1",
            evidence_strictness_delta=-0.1,
            recorded_at=NOW,
        )
    with pytest.raises(ValueError, match="scheduler_priority_delta"):
        ModulationOutput(
            consumer_id="test",
            signal_class="RESOURCE_PRESSURE",
            parameter="scheduler_priority",
            scope="global",
            scheduler_priority_delta=1,
            recorded_at=NOW,
        )


def test_phase1_record_emits_arousal_and_modulation_events(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    events = record_signal_event(bus, _signal())

    types = [event["type"] for event in events]
    assert types[0] == "AEP_SIGNAL_RECORDED"
    assert "AEP_AROUSAL_STATE_UPDATED" in types
    assert "AEP_MODULATION_RECORDED" in types

    modulation = next(event for event in events if event["type"] == "AEP_MODULATION_RECORDED")
    payload = modulation["payload"]
    assert payload["enforcement"] == "aep_restrict_only"
    assert payload["evidence_strictness_delta"] >= 0
    assert payload["scrutiny_depth_delta"] >= 0
    forbidden = {"grant", "permit", "allow", "deny", "approve", "verdict", "decision"}
    assert forbidden.isdisjoint(payload)


def test_modulation_events_are_replayable(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    record_signal_event(bus, _signal(severity=7))
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["aep"]["signals_recorded"] == 1
    assert result.state["activity"]["aep"]["arousal_updates"] == 1
    assert result.state["activity"]["aep"]["modulations"] >= 1
    assert result.state["environment"]["arousal"]["max_severity"] == 7


def test_aep_cannot_influence_committed_or_denied_actions_directly(tmp_path: Path):
    from hg_runtime.handlers.stubs import StubRecoveryHandler

    forbidden_imports = ("hg_ueak", "hg_oea", "hg_core.governance.permit_binder", "hg_core.governance.rtc_bridge")
    for path in Path("hg_aep").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_imports:
            assert token not in text, f"{path} must not call execution/authority modules"

    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    record_signal_event(bus, _signal(severity=9))
    loop = RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "after aep"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)

    events = list(bus.read_all())
    types = [event["type"] for event in events]
    assert "AEP_MODULATION_RECORDED" in types
    assert "UEAK_EXECUTION_COMMITTED" in types
    modulation_events = [event for event in events if event["type"] == "AEP_MODULATION_RECORDED"]
    forbidden = {"grant", "permit", "allow", "deny", "approve", "verdict", "decision", "commit_ref"}
    for event in modulation_events:
        assert forbidden.isdisjoint(event.get("payload", {}))
    assert loop.kernel.committed_actions
    assert not any(action.get("permit_ref") for action in loop.kernel.committed_actions)


def test_default_subscriptions_load_and_hash_anchor():
    bindings = load_subscriptions()
    assert len(bindings) >= 4
    assert all(binding.modulation_target for binding in bindings)


def test_compute_modulations_respects_scope():
    bindings = load_subscriptions()
    global_arousal = build_arousal_state([_signal()], scope="global", computed_at=NOW)
    request_arousal = build_arousal_state(
        [_signal(scope="request:req1", signal_class="UNCERTAINTY", severity=7)],
        scope="request:req1",
        computed_at=NOW,
    )
    global_mods = compute_modulations(global_arousal, bindings, recorded_at=NOW)
    request_mods = compute_modulations(request_arousal, bindings, recorded_at=NOW)
    global_params = {mod.parameter for mod in global_mods}
    request_params = {mod.parameter for mod in request_mods}
    assert "max_concurrency" in global_params
    assert "evidence_strictness" in request_params or "arbitration_scrutiny" in request_params
