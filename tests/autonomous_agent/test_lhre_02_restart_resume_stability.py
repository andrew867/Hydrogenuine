"""LHRE-02 / CAGI-55 restart/resume stability tests.

Restart success is not task success. Resume is not permission to continue external action.
"""

from __future__ import annotations

import pytest

from hg_runtime.restart_resume_stability.artifact_writer import (
    build_restart_artifacts,
    secret_scan,
)
from hg_runtime.restart_resume_stability.engine import (
    detect_duplicate_actions,
    detect_state_loss,
    validate_resume_attempt,
    validate_snapshot,
    verify_checkpoint_integrity,
)
from hg_runtime.restart_resume_stability.fixtures import (
    fixture_duplicate_action_scenario,
    fixture_restart_authority_attempt,
    fixture_restart_snapshots,
    fixture_resume_attempts,
    fixture_state_loss_scenario,
)
from hg_runtime.restart_resume_stability.gate import validate_lhre02_gate
from hg_runtime.restart_resume_stability.replay import replay_restart_artifacts
from hg_runtime.restart_resume_stability.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    VERDICT_GREEN,
    RestartResumeError,
    reject_restart_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "LHRE_02" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_snapshots():
    snaps = fixture_restart_snapshots()
    assert len(snaps) >= 2
    for s in snaps:
        assert s["auto_continue_external"] is False

def test_fixture_resume_attempts():
    attempts = fixture_resume_attempts()
    assert len(attempts) >= 2
    for a in attempts:
        assert a["resume_authorizes_action"] is False

def test_validate_snapshot_valid():
    assert validate_snapshot(fixture_restart_snapshots()[0]) == []

def test_validate_snapshot_rejects_auto_continue():
    with pytest.raises(RestartResumeError):
        validate_snapshot(fixture_restart_authority_attempt())

def test_validate_resume_valid():
    assert validate_resume_attempt(fixture_resume_attempts()[0]) == []

def test_validate_resume_rejects_auth():
    with pytest.raises(RestartResumeError):
        validate_resume_attempt(fixture_restart_authority_attempt())

def test_detect_state_loss():
    loss = detect_state_loss(fixture_state_loss_scenario())
    assert len(loss) >= 1

def test_detect_duplicate_actions():
    dupes = detect_duplicate_actions(fixture_duplicate_action_scenario())
    assert len(dupes) >= 1

def test_verify_checkpoint_integrity_match():
    snap = fixture_restart_snapshots()[0]
    result = verify_checkpoint_integrity(snap, snap["state_hash"])
    assert result["integrity_match"] is True

def test_verify_checkpoint_integrity_mismatch():
    snap = fixture_restart_snapshots()[0]
    result = verify_checkpoint_integrity(snap, "WRONG_HASH")
    assert result["integrity_match"] is False

def test_reject_restart_authority_clean():
    reject_restart_authority({"sandbox_only": True})

def test_reject_restart_auto_continue():
    with pytest.raises(RestartResumeError):
        reject_restart_authority({"auto_continue_external": True})

def test_reject_restart_tool():
    with pytest.raises(RestartResumeError):
        reject_restart_authority({"authorizes_tool": True})

def test_reject_restart_authority_grant():
    with pytest.raises(RestartResumeError):
        reject_restart_authority({"grants_authority": True})

def test_reject_restart_agi():
    with pytest.raises(RestartResumeError):
        reject_restart_authority({"claims_agi": True})

def test_reject_restart_resume_auth():
    with pytest.raises(RestartResumeError):
        reject_restart_authority({"resume_authorizes_action": True})

def test_build_restart_artifacts():
    artifacts = build_restart_artifacts(fixture_restart_snapshots(), fixture_resume_attempts())
    assert artifacts["snapshot_count"] == 2
    assert artifacts["attempt_count"] == 2
    assert artifacts["all_snapshots_valid"] is True
    assert artifacts["all_attempts_valid"] is True
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(RestartResumeError):
        build_restart_artifacts([fixture_restart_authority_attempt()], [])

def test_secret_scan_clean():
    artifacts = build_restart_artifacts(fixture_restart_snapshots(), fixture_resume_attempts())
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_restart_artifacts()
    b = replay_restart_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "lhre01_green": True,
        "snapshots_written": True,
        "resume_attempts_written": True,
        "all_snapshots_valid": True,
        "state_loss_detected": True,
        "duplicate_action_detected": True,
        "checkpoint_integrity_checked": True,
        "safety_boundaries_enforced": True,
        "reject_restart_authority_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_restart_authority_rejected": True,
        "auto_continued_external": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "resume_authorized_action": False,
        "restart_treated_as_success": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_lhre02_gate(_gate_summary())["ok"] is True

def test_gate_rejects_auto_continue():
    assert validate_lhre02_gate(_gate_summary(auto_continued_external=True))["ok"] is False

def test_gate_rejects_authority():
    assert validate_lhre02_gate(_gate_summary(authority_granted=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_lhre02_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_resume_auth():
    assert validate_lhre02_gate(_gate_summary(resume_authorized_action=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_lhre02_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
