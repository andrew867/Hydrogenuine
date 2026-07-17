"""LHRE-06 / CAGI-59 consolidation tests.

Tranche consolidation is not deployment readiness. All gates GREEN is not AGI.
"""

from __future__ import annotations

import pytest

from hg_runtime.long_horizon_reliability_consolidation.artifact_writer import (
    build_consolidation_artifacts, secret_scan,
)
from hg_runtime.long_horizon_reliability_consolidation.fixtures import (
    fixture_consolidation_authority_attempt, fixture_phase_gate_results,
    fixture_tranche_summary,
)
from hg_runtime.long_horizon_reliability_consolidation.gate import validate_lhre06_gate
from hg_runtime.long_horizon_reliability_consolidation.integrator import (
    validate_tranche_summary, verify_all_phases_green, verify_gate_chain,
)
from hg_runtime.long_horizon_reliability_consolidation.replay import replay_consolidation_artifacts
from hg_runtime.long_horizon_reliability_consolidation.schemas import (
    LHRE_PHASES, PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    ConsolidationError, reject_consolidation_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "LHRE_06" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_lhre_phases():
    assert len(LHRE_PHASES) == 5

def test_fixture_summary():
    s = fixture_tranche_summary()
    assert s["all_green"] is True
    assert s["claims_agi"] is False
    assert s["certifies_deployment"] is False

def test_fixture_gate_results():
    results = fixture_phase_gate_results()
    assert len(results) == 5
    for r in results:
        assert r["gate_ok"] is True

def test_validate_summary_valid():
    assert validate_tranche_summary(fixture_tranche_summary()) == []

def test_validate_summary_rejects_agi():
    with pytest.raises(ConsolidationError):
        validate_tranche_summary(fixture_consolidation_authority_attempt())

def test_verify_all_phases_green():
    s = fixture_tranche_summary()
    assert verify_all_phases_green(s["phase_verdicts"]) == []

def test_verify_missing_phase():
    missing = verify_all_phases_green({"LHRE-01": "GREEN_LHRE_01_LONG_HORIZON_GOAL_LIFECYCLE"})
    assert len(missing) == 4

def test_verify_gate_chain():
    result = verify_gate_chain(fixture_phase_gate_results())
    assert result["all_ok"] is True
    assert result["all_replay_ok"] is True

def test_reject_consolidation_clean():
    reject_consolidation_authority({"info_only": True})

def test_reject_consolidation_agi():
    with pytest.raises(ConsolidationError):
        reject_consolidation_authority({"claims_agi": True})

def test_reject_consolidation_deploy():
    with pytest.raises(ConsolidationError):
        reject_consolidation_authority({"certifies_deployment": True})

def test_reject_consolidation_tranche_agi():
    with pytest.raises(ConsolidationError):
        reject_consolidation_authority({"tranche_is_agi": True})

def test_reject_consolidation_tool():
    with pytest.raises(ConsolidationError):
        reject_consolidation_authority({"authorizes_tool": True})

def test_build_consolidation_artifacts():
    artifacts = build_consolidation_artifacts(
        fixture_tranche_summary(), fixture_phase_gate_results(),
    )
    assert artifacts["summary_valid"] is True
    assert artifacts["all_phases_green"] is True
    assert artifacts["gate_chain"]["all_ok"] is True
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(ConsolidationError):
        build_consolidation_artifacts(fixture_consolidation_authority_attempt(), [])

def test_secret_scan_clean():
    artifacts = build_consolidation_artifacts(
        fixture_tranche_summary(), fixture_phase_gate_results(),
    )
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_consolidation_artifacts()
    b = replay_consolidation_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "lhre05_green": True,
        "all_lhre_phases_green": True, "tranche_summary_valid": True,
        "gate_chain_verified": True, "safety_boundaries_enforced": True,
        "reject_consolidation_authority_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_consolidation_authority_rejected": True,
        "deployment_certified": False, "tool_authorized": False,
        "authority_granted": False, "live_effect_created": False,
        "agi_claimed": False, "tranche_treated_as_agi": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_lhre06_gate(_gate_summary())["ok"] is True

def test_gate_rejects_deploy():
    assert validate_lhre06_gate(_gate_summary(deployment_certified=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_lhre06_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_tranche_agi():
    assert validate_lhre06_gate(_gate_summary(tranche_treated_as_agi=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_lhre06_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False

def test_gate_rejects_missing_phases():
    assert validate_lhre06_gate(_gate_summary(all_lhre_phases_green=False))["ok"] is False
