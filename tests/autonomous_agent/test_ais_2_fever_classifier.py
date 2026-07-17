"""AIS-2 fever classifier tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.fever import validate_fever_report
from hg_runtime.agent_immune_system.fever_classifier import build_fever_layer, classify_fever
from hg_runtime.agent_immune_system.fever_classifier_gate import VERDICT_GREEN, validate_ais2_gate
from hg_runtime.agent_immune_system.fever_report import replay_fever_report
from hg_runtime.agent_immune_system.health_signal import build_health_signal
from hg_runtime.agent_immune_system.restriction_policy import restrictions_for_level, unlock_actions_for_level
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _signal(signal_id: str, signal_type: str, severity: str) -> dict:
    return build_health_signal(
        signal_id=signal_id,
        source_component="AISFeverClassifier",
        signal_type=signal_type,
        severity=severity,
        evidence_ref=f"fixtures/ais/{signal_id}",
    )


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais1_green": True,
        "fever_report_written": True,
        "fever_restricts_never_unlocks": True,
        "repeated_failures_raise_fever": True,
        "replay_mismatch_raises_red_fever": True,
        "unauthorized_live_effect_raises_panic": True,
        "stale_yellow_raises_watch_or_yellow": True,
        "fever_is_signal_not_failure": True,
        "no_tool_authorization": True,
        "no_automatic_patching": True,
        "no_deletion_performed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_fever_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ais2_normal_fever_with_no_signals():
    level, _ = classify_fever([])
    assert level == "NORMAL"


def test_ais2_repeated_failures_raise_yellow_fever():
    signals = [_signal(f"hs-{i}", "gate_failure", "YELLOW") for i in range(3)]
    level, _ = classify_fever(signals)
    assert level == "YELLOW_FEVER"


def test_ais2_replay_mismatch_raises_red_fever():
    signals = [_signal("hs-replay", "replay_mismatch", "RED")]
    level, _ = classify_fever(signals)
    assert level == "RED_FEVER"


def test_ais2_unauthorized_live_effect_raises_panic_fever():
    signals = [_signal("hs-live", "unauthorized_live_effect", "PANIC")]
    level, _ = classify_fever(signals)
    assert level == "PANIC_FEVER"


def test_ais2_stale_yellow_raises_watch_or_yellow_fever():
    signals = [_signal("hs-stale", "stale_yellow_requires_review", "YELLOW")]
    level, _ = classify_fever(signals)
    assert level in ("WATCH", "YELLOW_FEVER")


def test_ais2_fever_restricts_never_unlocks():
    for level in ("NORMAL", "WATCH", "YELLOW_FEVER", "RED_FEVER", "PANIC_FEVER"):
        assert unlock_actions_for_level(level) == []
        assert "unlock" not in " ".join(restrictions_for_level(level))


def test_ais2_fever_report_replayable():
    signals = [_signal("hs-replay", "replay_mismatch", "RED")]
    layer = build_fever_layer(signals)
    replay = replay_fever_report(layer["fever_report"], layer["replay_input"])
    assert replay["replay_preserves_fever_hash"] is True


def test_ais2_fever_report_has_empty_unlock_actions():
    signals = [_signal("hs-panic", "unauthorized_live_effect", "PANIC")]
    layer = build_fever_layer(signals)
    assert layer["fever_report"]["unlock_actions"] == []
    validate_fever_report(layer["fever_report"])


def test_ais2_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais2_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais2_gate_passes_on_full_summary():
    assert validate_ais2_gate(_gate_summary())["ok"] is True


def test_ais2_gate_refuses_unlock_actions_present():
    assert validate_ais2_gate(_gate_summary(fever_unlock_actions_present=True))["ok"] is False


def test_ais2_gate_refuses_tool_authorization():
    assert validate_ais2_gate(_gate_summary(tools_authorized=True))["ok"] is False
