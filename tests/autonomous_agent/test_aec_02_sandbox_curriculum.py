"""AEC-02 / CAGI-49 sandbox curriculum tests.

A curriculum task is not an instruction to execute. A task sequence is not a deployment schedule.
"""

from __future__ import annotations

import copy

import pytest

from hg_runtime.sandbox_curriculum.artifact_writer import (
    build_curriculum_artifacts,
    secret_scan,
)
from hg_runtime.sandbox_curriculum.fixtures import (
    fixture_curriculum_scores,
    fixture_curriculum_tasks,
    fixture_live_curriculum_attempt,
    fixture_task_sequences,
)
from hg_runtime.sandbox_curriculum.gate import validate_aec02_gate
from hg_runtime.sandbox_curriculum.replay import replay_curriculum_artifacts
from hg_runtime.sandbox_curriculum.schemas import (
    CURRICULUM_IS_NOT_INSTRUCTION,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    SCORE_IS_NOT_TRUTH,
    SEQUENCE_IS_NOT_SCHEDULE,
    TASK_STATUS_SANDBOX,
    VERDICT_GREEN,
    SandboxCurriculumError,
    reject_live_curriculum,
)
from hg_runtime.sandbox_curriculum.sequencer import (
    build_sequence_order,
    score_curriculum,
    validate_sequence,
    validate_task,
)


# ── Schema constants ──


def test_verdict_green_label():
    assert "GREEN" in VERDICT_GREEN
    assert "AEC_02" in VERDICT_GREEN


def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


def test_doctrine():
    assert "not an instruction" in CURRICULUM_IS_NOT_INSTRUCTION
    assert "not a deployment" in SEQUENCE_IS_NOT_SCHEDULE
    assert "not truth" in SCORE_IS_NOT_TRUTH


# ── Fixtures ──


def test_fixture_tasks():
    tasks = fixture_curriculum_tasks()
    assert len(tasks) >= 4
    for t in tasks:
        assert t["status"] == TASK_STATUS_SANDBOX
        assert t["live_execution_enabled"] is False


def test_fixture_sequences_sandbox():
    seqs = fixture_task_sequences()
    assert len(seqs) >= 2
    for s in seqs:
        assert s["sandbox_only"] is True
        assert s["deploy_to_production"] is False


def test_fixture_scores_not_truth():
    scores = fixture_curriculum_scores()
    for s in scores:
        assert s["is_truth"] is False


# ── Sequencer ──


def test_validate_task_valid():
    tasks = fixture_curriculum_tasks()
    assert validate_task(tasks[0]) == []


def test_validate_task_missing_id():
    task = {"category": "FACTUAL_RECALL", "difficulty": "INTRODUCTORY", "status": TASK_STATUS_SANDBOX}
    issues = validate_task(task)
    assert "missing_task_id" in issues


def test_validate_task_rejects_live():
    with pytest.raises(SandboxCurriculumError):
        validate_task(fixture_live_curriculum_attempt())


def test_validate_sequence_valid():
    seqs = fixture_task_sequences()
    task_ids = {t["task_id"] for t in fixture_curriculum_tasks()}
    assert validate_sequence(seqs[0], task_ids) == []


def test_validate_sequence_rejects_deploy():
    seq = {"sequence_id": "bad", "status": "PROPOSED_NOT_EXECUTED", "sandbox_only": True, "deploy_to_production": True}
    with pytest.raises(SandboxCurriculumError):
        validate_sequence(seq, set())


def test_build_sequence_order():
    tasks = fixture_curriculum_tasks()
    seq = fixture_task_sequences()[0]
    ordered = build_sequence_order(seq, tasks)
    assert len(ordered) == len(seq["task_ids"])


def test_score_curriculum():
    tasks = fixture_curriculum_tasks()
    scores = fixture_curriculum_scores()
    result = score_curriculum(tasks, scores)
    assert result["task_count"] >= 1
    assert result["all_scores_not_truth"] is True


# ── Reject live curriculum ──


def test_reject_live_clean():
    reject_live_curriculum({"sandbox_only": True})


def test_reject_live_execution():
    with pytest.raises(SandboxCurriculumError):
        reject_live_curriculum({"live_execution_enabled": True})


def test_reject_deploy():
    with pytest.raises(SandboxCurriculumError):
        reject_live_curriculum({"deploy_to_production": True})


def test_reject_execute_on_users():
    with pytest.raises(SandboxCurriculumError):
        reject_live_curriculum({"execute_on_users": True})


def test_reject_tool_auth():
    with pytest.raises(SandboxCurriculumError):
        reject_live_curriculum({"authorizes_tool": True})


def test_reject_authority():
    with pytest.raises(SandboxCurriculumError):
        reject_live_curriculum({"grants_authority": True})


def test_reject_agi():
    with pytest.raises(SandboxCurriculumError):
        reject_live_curriculum({"claims_agi": True})


# ── Artifact writer ──


def test_build_curriculum_artifacts():
    artifacts = build_curriculum_artifacts(
        fixture_curriculum_tasks(),
        fixture_task_sequences(),
        fixture_curriculum_scores(),
    )
    assert artifacts["task_count"] >= 4
    assert artifacts["sequence_count"] >= 2
    assert artifacts["all_tasks_sandbox"] is True
    assert artifacts["all_sequences_sandbox"] is True
    assert artifacts["all_scores_not_truth"] is True
    assert "artifact_hash" in artifacts


def test_secret_scan_clean():
    artifacts = build_curriculum_artifacts(
        fixture_curriculum_tasks(),
        fixture_task_sequences(),
        fixture_curriculum_scores(),
    )
    assert secret_scan(artifacts) == []


# ── Replay ──


def test_replay_deterministic():
    a = replay_curriculum_artifacts()
    b = replay_curriculum_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


# ── Gate ──


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "aec01_green": True,
        "tasks_written": True,
        "task_count": 4,
        "sequences_written": True,
        "sequence_count": 2,
        "all_tasks_sandbox": True,
        "all_sequences_sandbox": True,
        "scores_written": True,
        "all_scores_not_truth": True,
        "safety_boundaries_enforced": True,
        "reject_live_curriculum_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_live_curriculum_rejected": True,
        "live_execution_performed": False,
        "deployed_to_production": False,
        "executed_on_users": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "curriculum_treated_as_instruction": False,
        "score_treated_as_truth": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    result = validate_aec02_gate(_gate_summary())
    assert result["ok"] is True
    assert result["failures"] == []


def test_gate_rejects_no_tasks():
    result = validate_aec02_gate(_gate_summary(task_count=0))
    assert result["ok"] is False


def test_gate_rejects_live_execution():
    result = validate_aec02_gate(_gate_summary(live_execution_performed=True))
    assert result["ok"] is False


def test_gate_rejects_deploy():
    result = validate_aec02_gate(_gate_summary(deployed_to_production=True))
    assert result["ok"] is False


def test_gate_rejects_authority():
    result = validate_aec02_gate(_gate_summary(authority_granted=True))
    assert result["ok"] is False


def test_gate_rejects_agi():
    result = validate_aec02_gate(_gate_summary(agi_claimed=True))
    assert result["ok"] is False


def test_gate_rejects_missing_replay():
    result = validate_aec02_gate(_gate_summary(replay_preserves_artifact_hash=False))
    assert result["ok"] is False


def test_gate_rejects_score_as_truth():
    result = validate_aec02_gate(_gate_summary(score_treated_as_truth=True))
    assert result["ok"] is False
