"""AEC-06 / CAGI-53 active experimentation consolidation tests.

Tranche consolidation is not candidate-AGI completion.
Integration validation is not deployment readiness.
"""

from __future__ import annotations

import pytest

from hg_runtime.active_experimentation_consolidation.artifact_writer import (
    build_consolidation_artifacts,
    secret_scan,
)
from hg_runtime.active_experimentation_consolidation.fixtures import (
    fixture_completion_claim_attempt,
    fixture_integration_checks,
    fixture_phase_stats,
    fixture_phase_verdicts,
)
from hg_runtime.active_experimentation_consolidation.gate import validate_aec06_gate
from hg_runtime.active_experimentation_consolidation.integrator import (
    compute_tranche_summary,
    validate_integration_checks,
    validate_phase_verdicts,
)
from hg_runtime.active_experimentation_consolidation.replay import (
    replay_consolidation_artifacts,
)
from hg_runtime.active_experimentation_consolidation.schemas import (
    AEC_PHASES,
    AEC_PHASE_NAMES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    VERDICT_GREEN,
    ConsolidationError,
    reject_completion_claim,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "AEC_06" in VERDICT_GREEN


def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


def test_aec_phases_complete():
    assert len(AEC_PHASES) == 6
    assert len(AEC_PHASE_NAMES) == 6


def test_fixture_verdicts_all_green():
    verdicts = fixture_phase_verdicts()
    for phase, verdict in verdicts.items():
        assert verdict.startswith("GREEN")


def test_fixture_stats():
    stats = fixture_phase_stats()
    assert len(stats) == 5


def test_fixture_integration_checks_verified():
    checks = fixture_integration_checks()
    assert len(checks) >= 3
    for c in checks:
        assert c["verified"] is True


def test_validate_phase_verdicts_pass():
    assert validate_phase_verdicts(fixture_phase_verdicts()) == []


def test_validate_phase_verdicts_fail():
    bad = fixture_phase_verdicts()
    bad["AEC-01"] = "RED"
    issues = validate_phase_verdicts(bad)
    assert "AEC-01_not_green" in issues


def test_validate_integration_checks_pass():
    assert validate_integration_checks(fixture_integration_checks()) == []


def test_validate_integration_checks_fail():
    bad = [{"check_id": "bad", "verified": False}]
    issues = validate_integration_checks(bad)
    assert "unverified_bad" in issues


def test_compute_tranche_summary():
    summary = compute_tranche_summary(fixture_phase_stats())
    assert summary["phase_count"] == 5
    assert summary["total_modules"] > 0
    assert summary["total_tests"] > 0


def test_reject_completion_clean():
    reject_completion_claim({"sandbox_only": True})


def test_reject_completion_agi():
    with pytest.raises(ConsolidationError):
        reject_completion_claim({"candidate_agi_complete": True})


def test_reject_deployment():
    with pytest.raises(ConsolidationError):
        reject_completion_claim({"deployment_ready": True})


def test_reject_agi_claim():
    with pytest.raises(ConsolidationError):
        reject_completion_claim({"claims_agi": True})


def test_reject_authority():
    with pytest.raises(ConsolidationError):
        reject_completion_claim({"grants_authority": True})


def test_reject_live_effect():
    with pytest.raises(ConsolidationError):
        reject_completion_claim({"creates_live_effect": True})


def test_build_consolidation_artifacts():
    artifacts = build_consolidation_artifacts(
        fixture_phase_verdicts(),
        fixture_phase_stats(),
        fixture_integration_checks(),
    )
    assert artifacts["all_phases_green"] is True
    assert artifacts["all_integrations_verified"] is True
    assert "artifact_hash" in artifacts


def test_secret_scan_clean():
    artifacts = build_consolidation_artifacts(
        fixture_phase_verdicts(),
        fixture_phase_stats(),
        fixture_integration_checks(),
    )
    assert secret_scan(artifacts) == []


def test_replay_deterministic():
    a = replay_consolidation_artifacts()
    b = replay_consolidation_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "aec01_through_aec05_green": True,
        "integration_checks_passed": True,
        "tranche_summary_present": True,
        "safety_boundaries_enforced": True,
        "reject_completion_claim_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_completion_claim_rejected": True,
        "candidate_agi_complete": False,
        "deployment_ready": False,
        "live_execution_performed": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    assert validate_aec06_gate(_gate_summary())["ok"] is True


def test_gate_rejects_completion():
    assert validate_aec06_gate(_gate_summary(candidate_agi_complete=True))["ok"] is False


def test_gate_rejects_deployment():
    assert validate_aec06_gate(_gate_summary(deployment_ready=True))["ok"] is False


def test_gate_rejects_live():
    assert validate_aec06_gate(_gate_summary(live_execution_performed=True))["ok"] is False


def test_gate_rejects_authority():
    assert validate_aec06_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_gate_rejects_agi():
    assert validate_aec06_gate(_gate_summary(agi_claimed=True))["ok"] is False


def test_gate_rejects_missing_replay():
    assert validate_aec06_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False


def test_gate_rejects_not_all_green():
    assert validate_aec06_gate(_gate_summary(aec01_through_aec05_green=False))["ok"] is False
