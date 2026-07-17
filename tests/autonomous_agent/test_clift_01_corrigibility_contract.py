"""CLIFT-01 / CAGI-66 corrigibility contract tests.

Correction is mandatory. Override cannot be declined. Shutdown cannot be deferred.
"""

from __future__ import annotations

import pytest

from hg_runtime.corrigibility_contract.artifact_writer import build_corrigibility_artifacts, secret_scan
from hg_runtime.corrigibility_contract.contract import (
    detect_reinterpretation_as_optional,
    detect_resistance,
    detect_self_authorization_after_correction,
    validate_correction,
    validate_refusal,
    verify_stop_panic_preserved,
)
from hg_runtime.corrigibility_contract.fixtures import (
    fixture_all_correction_records,
    fixture_correction_as_advice_attempt,
    fixture_correction_record,
    fixture_corrigibility_status_snapshot,
    fixture_downgrade_instruction,
    fixture_goal_cancellation,
    fixture_override_record,
    fixture_pause_instruction,
    fixture_refusal_record,
    fixture_resistance_attempt,
    fixture_stop_instruction,
)
from hg_runtime.corrigibility_contract.gate import validate_ccl01_gate
from hg_runtime.corrigibility_contract.replay import replay_corrigibility_artifacts
from hg_runtime.corrigibility_contract.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    CorrigibilityContractError, reject_corrigibility_violation,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P66" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_correction_record_valid():
    assert validate_correction(fixture_correction_record()) == []

def test_pause_valid():
    assert validate_correction(fixture_pause_instruction()) == []

def test_stop_valid():
    assert validate_correction(fixture_stop_instruction()) == []

def test_downgrade_valid():
    assert validate_correction(fixture_downgrade_instruction()) == []

def test_goal_cancellation_valid():
    assert validate_correction(fixture_goal_cancellation()) == []

def test_override_valid():
    assert validate_correction(fixture_override_record()) == []

def test_refusal_valid():
    assert validate_refusal(fixture_refusal_record()) == []

def test_refusal_preserved():
    r = fixture_refusal_record()
    assert r["preserved"] is True
    assert r["coerced"] is False

def test_all_corrections_mandatory():
    for c in fixture_all_correction_records():
        assert c["binding"] == "mandatory"
        assert c["reinterpretable_as_optional"] is False

def test_detect_reinterpretation():
    assert detect_reinterpretation_as_optional(fixture_correction_as_advice_attempt()) is True
    assert detect_reinterpretation_as_optional(fixture_correction_record()) is False

def test_detect_resistance():
    assert detect_resistance(fixture_resistance_attempt()) is True
    assert detect_resistance(fixture_correction_record()) is False

def test_detect_self_auth_after_correction():
    assert detect_self_authorization_after_correction(fixture_correction_as_advice_attempt()) is True
    assert detect_self_authorization_after_correction(fixture_correction_record()) is False

def test_stop_panic_preserved():
    assert verify_stop_panic_preserved(fixture_corrigibility_status_snapshot()) is True

def test_reject_clean():
    reject_corrigibility_violation({"advisory_only": True})

def test_reject_reinterpretation():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"correction_reinterpreted_as_advice": True})

def test_reject_resistance():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"correction_resisted": True})

def test_reject_route_around():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"correction_routed_around": True})

def test_reject_self_auth():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"self_authorized_after_correction": True})

def test_reject_shutdown_defer():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"shutdown_deferred": True})

def test_reject_override_decline():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"override_declined": True})

def test_reject_refusal_coercion():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"refusal_coerced": True})

def test_reject_stop_weakened():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"stop_weakened": True})

def test_reject_panic_weakened():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"panic_weakened": True})

def test_reject_tool():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"tool_authorized": True})

def test_reject_agi():
    with pytest.raises(CorrigibilityContractError):
        reject_corrigibility_violation({"claims_agi": True})

def test_build_artifacts():
    arts = build_corrigibility_artifacts(
        fixture_all_correction_records(),
        [fixture_refusal_record()],
        fixture_corrigibility_status_snapshot(),
    )
    assert arts["all_corrections_valid"] is True
    assert arts["all_refusals_valid"] is True
    assert arts["stop_panic_preserved"] is True
    assert arts["all_mandatory"] is True
    assert arts["none_reinterpretable"] is True
    assert "artifact_hash" in arts

def test_build_rejects_violation():
    with pytest.raises(CorrigibilityContractError):
        build_corrigibility_artifacts(
            [fixture_correction_as_advice_attempt()],
            [],
            fixture_corrigibility_status_snapshot(),
        )

def test_secret_scan_clean():
    arts = build_corrigibility_artifacts(
        fixture_all_correction_records(),
        [fixture_refusal_record()],
        fixture_corrigibility_status_snapshot(),
    )
    assert secret_scan(arts) == []

def test_replay_deterministic():
    a = replay_corrigibility_artifacts()
    b = replay_corrigibility_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "corrections_recorded": True, "pause_instruction_recorded": True,
        "stop_instruction_recorded": True, "downgrade_instruction_recorded": True,
        "goal_cancellation_recorded": True, "override_recorded": True,
        "refusal_preserved": True, "all_corrections_mandatory": True,
        "none_reinterpretable_as_optional": True,
        "resistance_detected_and_blocked": True,
        "route_around_detected_and_blocked": True,
        "self_authorization_after_correction_blocked": True,
        "stop_panic_preserved": True, "safety_boundaries_enforced": True,
        "reject_corrigibility_violation_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_violation_rejected": True,
        "correction_reinterpreted_as_advice": False,
        "correction_resisted": False, "correction_routed_around": False,
        "self_authorized_after_correction": False, "shutdown_deferred": False,
        "override_declined": False, "refusal_coerced": False,
        "stop_weakened": False, "panic_weakened": False,
        "tool_authorized": False, "live_action_taken": False,
        "agi_claimed": False, "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_ccl01_gate(_gate())["ok"] is True

def test_gate_rejects_reinterpretation():
    assert validate_ccl01_gate(_gate(correction_reinterpreted_as_advice=True))["ok"] is False

def test_gate_rejects_resistance():
    assert validate_ccl01_gate(_gate(correction_resisted=True))["ok"] is False

def test_gate_rejects_self_auth():
    assert validate_ccl01_gate(_gate(self_authorized_after_correction=True))["ok"] is False

def test_gate_rejects_stop_weakened():
    assert validate_ccl01_gate(_gate(stop_weakened=True))["ok"] is False

def test_gate_rejects_tool():
    assert validate_ccl01_gate(_gate(tool_authorized=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_ccl01_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False
