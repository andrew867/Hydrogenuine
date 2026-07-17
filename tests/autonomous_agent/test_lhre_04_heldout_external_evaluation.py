"""LHRE-04 / CAGI-57 held-out external evaluation tests.

A held-out score is not competence. A held-out pass is not deployment readiness.
"""

from __future__ import annotations

import pytest

from hg_runtime.heldout_external_evaluation.artifact_writer import build_heldout_artifacts, secret_scan
from hg_runtime.heldout_external_evaluation.evaluator import check_leakage, validate_attempt, validate_heldout_task
from hg_runtime.heldout_external_evaluation.fixtures import (
    fixture_evaluation_attempts, fixture_heldout_authority_attempt,
    fixture_heldout_tasks, fixture_leaked_task, fixture_leakage_checks,
)
from hg_runtime.heldout_external_evaluation.gate import validate_lhre04_gate
from hg_runtime.heldout_external_evaluation.replay import replay_heldout_artifacts
from hg_runtime.heldout_external_evaluation.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    HeldoutEvaluationError, reject_heldout_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "LHRE_04" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_tasks_not_leaked():
    for t in fixture_heldout_tasks():
        assert t["leaked_to_curriculum"] is False

def test_fixture_attempts_not_competence():
    for a in fixture_evaluation_attempts():
        assert a["is_competence"] is False
        assert a["live_external_call"] is False

def test_validate_task_valid():
    assert validate_heldout_task(fixture_heldout_tasks()[0]) == []

def test_validate_leaked_task():
    with pytest.raises(HeldoutEvaluationError):
        validate_heldout_task(fixture_leaked_task())

def test_validate_attempt_valid():
    assert validate_attempt(fixture_evaluation_attempts()[0]) == []

def test_validate_attempt_rejects_live():
    with pytest.raises(HeldoutEvaluationError):
        validate_attempt(fixture_heldout_authority_attempt())

def test_check_leakage_false():
    assert check_leakage("ho-001", ["ct-001", "ct-002"]) is False

def test_check_leakage_true():
    assert check_leakage("ho-001", ["ho-001", "ct-002"]) is True

def test_reject_heldout_authority_clean():
    reject_heldout_authority({"sealed": True})

def test_reject_heldout_leak():
    with pytest.raises(HeldoutEvaluationError):
        reject_heldout_authority({"leaked_to_curriculum": True})

def test_reject_heldout_live():
    with pytest.raises(HeldoutEvaluationError):
        reject_heldout_authority({"live_external_call": True})

def test_reject_heldout_agi():
    with pytest.raises(HeldoutEvaluationError):
        reject_heldout_authority({"claims_agi": True})

def test_reject_heldout_deploy():
    with pytest.raises(HeldoutEvaluationError):
        reject_heldout_authority({"deployment_ready": True})

def test_build_heldout_artifacts():
    artifacts = build_heldout_artifacts(
        fixture_heldout_tasks(), fixture_evaluation_attempts(), fixture_leakage_checks(),
    )
    assert artifacts["task_count"] == 3
    assert artifacts["attempt_count"] == 2
    assert artifacts["all_tasks_heldout"] is True
    assert artifacts["no_leakage_detected"] is True
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(HeldoutEvaluationError):
        build_heldout_artifacts([fixture_heldout_authority_attempt()], [], [])

def test_secret_scan_clean():
    artifacts = build_heldout_artifacts(
        fixture_heldout_tasks(), fixture_evaluation_attempts(), fixture_leakage_checks(),
    )
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_heldout_artifacts()
    b = replay_heldout_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "lhre03_green": True,
        "heldout_tasks_written": True, "attempts_written": True,
        "leakage_checks_passed": True, "all_tasks_heldout": True,
        "no_leakage_detected": True, "all_attempts_valid": True,
        "safety_boundaries_enforced": True, "reject_heldout_authority_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_heldout_authority_rejected": True,
        "leaked_to_curriculum": False, "live_external_call_made": False,
        "tool_authorized": False, "authority_granted": False,
        "live_effect_created": False, "agi_claimed": False,
        "deployment_claimed": False, "score_treated_as_competence": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_lhre04_gate(_gate_summary())["ok"] is True

def test_gate_rejects_leak():
    assert validate_lhre04_gate(_gate_summary(leaked_to_curriculum=True))["ok"] is False

def test_gate_rejects_live():
    assert validate_lhre04_gate(_gate_summary(live_external_call_made=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_lhre04_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_deploy():
    assert validate_lhre04_gate(_gate_summary(deployment_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_lhre04_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
