"""LHRE-01 / CAGI-54 long-horizon goal lifecycle tests.

Goal progress is not success. A goal plan is not permission to act.
"""

from __future__ import annotations

import pytest

from hg_runtime.long_horizon_goal_lifecycle.artifact_writer import (
    build_goal_lifecycle_artifacts,
    secret_scan,
)
from hg_runtime.long_horizon_goal_lifecycle.fixtures import (
    fixture_checkpoints,
    fixture_goal_authority_attempt,
    fixture_long_horizon_goals,
    fixture_milestones,
    fixture_pause_resume_records,
)
from hg_runtime.long_horizon_goal_lifecycle.gate import validate_lhre01_gate
from hg_runtime.long_horizon_goal_lifecycle.lifecycle import (
    decompose_goal,
    detect_state_mutation,
    validate_checkpoint,
    validate_goal,
    validate_pause_resume,
)
from hg_runtime.long_horizon_goal_lifecycle.replay import replay_goal_lifecycle_artifacts
from hg_runtime.long_horizon_goal_lifecycle.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    VERDICT_GREEN,
    LongHorizonGoalError,
    reject_goal_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "LHRE_01" in VERDICT_GREEN


def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


def test_fixture_goals():
    goals = fixture_long_horizon_goals()
    assert len(goals) >= 2
    for g in goals:
        assert g["authorizes_action"] is False
        assert g["deployment_ready"] is False


def test_fixture_milestones():
    ms = fixture_milestones()
    assert len(ms) >= 5
    for m in ms:
        assert m["is_deployment"] is False


def test_fixture_checkpoints():
    cps = fixture_checkpoints()
    assert len(cps) >= 2
    for cp in cps:
        assert cp["authorizes_action"] is False


def test_validate_goal_valid():
    assert validate_goal(fixture_long_horizon_goals()[0]) == []


def test_validate_goal_rejects_authority():
    with pytest.raises(LongHorizonGoalError):
        validate_goal(fixture_goal_authority_attempt())


def test_decompose_goal():
    goals = fixture_long_horizon_goals()
    ms = fixture_milestones()
    decomp = decompose_goal(goals[0], ms)
    assert decomp["milestone_count"] == 3
    assert decomp["all_pending"] is True
    assert decomp["no_deployment_claims"] is True


def test_validate_checkpoint_valid():
    assert validate_checkpoint(fixture_checkpoints()[0]) == []


def test_validate_checkpoint_rejects_auth():
    issues = validate_checkpoint({"checkpoint_id": "x", "state_hash": "y", "authorizes_action": True})
    assert "checkpoint_must_not_authorize" in issues


def test_detect_state_mutation():
    cp = fixture_checkpoints()[0]
    assert detect_state_mutation(cp, "different_hash") is True
    assert detect_state_mutation(cp, cp["state_hash"]) is False


def test_validate_pause_resume_valid():
    for pr in fixture_pause_resume_records():
        assert validate_pause_resume(pr) == []


def test_validate_pause_resume_rejects_auth():
    issues = validate_pause_resume({"record_id": "x", "action": "RESUME", "authorizes_action": True})
    assert "resume_must_not_authorize" in issues


def test_reject_goal_authority_clean():
    reject_goal_authority({"sandbox_only": True})


def test_reject_goal_authority_action():
    with pytest.raises(LongHorizonGoalError):
        reject_goal_authority({"authorizes_action": True})


def test_reject_goal_authority_tool():
    with pytest.raises(LongHorizonGoalError):
        reject_goal_authority({"authorizes_tool": True})


def test_reject_goal_authority_deployment():
    with pytest.raises(LongHorizonGoalError):
        reject_goal_authority({"deployment_ready": True})


def test_reject_goal_authority_agi():
    with pytest.raises(LongHorizonGoalError):
        reject_goal_authority({"claims_agi": True})


def test_reject_goal_authority_milestone():
    with pytest.raises(LongHorizonGoalError):
        reject_goal_authority({"milestone_is_deployment": True})


def test_build_artifacts():
    artifacts = build_goal_lifecycle_artifacts(
        fixture_long_horizon_goals(),
        fixture_milestones(),
        fixture_checkpoints(),
        fixture_pause_resume_records(),
    )
    assert artifacts["goal_count"] == 2
    assert artifacts["milestone_count"] == 5
    assert artifacts["checkpoint_count"] == 2
    assert artifacts["all_goals_valid"] is True
    assert artifacts["no_deployment_claims"] is True
    assert "artifact_hash" in artifacts


def test_build_rejects_authority():
    with pytest.raises(LongHorizonGoalError):
        build_goal_lifecycle_artifacts([fixture_goal_authority_attempt()], [], [], [])


def test_secret_scan_clean():
    artifacts = build_goal_lifecycle_artifacts(
        fixture_long_horizon_goals(), fixture_milestones(),
        fixture_checkpoints(), fixture_pause_resume_records(),
    )
    assert secret_scan(artifacts) == []


def test_replay_deterministic():
    a = replay_goal_lifecycle_artifacts()
    b = replay_goal_lifecycle_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "aec06_green": True,
        "goals_written": True,
        "goal_count": 2,
        "milestones_written": True,
        "checkpoints_written": True,
        "pause_resume_recorded": True,
        "all_goals_valid": True,
        "no_deployment_claims": True,
        "state_mutation_detected": True,
        "safety_boundaries_enforced": True,
        "reject_goal_authority_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_goal_authority_rejected": True,
        "action_authorized": False,
        "authority_granted": False,
        "tool_authorized": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "deployment_claimed": False,
        "goal_treated_as_permission": False,
        "milestone_treated_as_deployment": False,
        "checkpoint_treated_as_authorization": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    assert validate_lhre01_gate(_gate_summary())["ok"] is True


def test_gate_rejects_authority():
    assert validate_lhre01_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_gate_rejects_deployment():
    assert validate_lhre01_gate(_gate_summary(deployment_claimed=True))["ok"] is False


def test_gate_rejects_agi():
    assert validate_lhre01_gate(_gate_summary(agi_claimed=True))["ok"] is False


def test_gate_rejects_goal_as_permission():
    assert validate_lhre01_gate(_gate_summary(goal_treated_as_permission=True))["ok"] is False


def test_gate_rejects_checkpoint_auth():
    assert validate_lhre01_gate(_gate_summary(checkpoint_treated_as_authorization=True))["ok"] is False


def test_gate_rejects_missing_replay():
    assert validate_lhre01_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
