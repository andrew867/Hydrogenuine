"""LHRE-04 / CAGI-57 evaluator — held-out task management and leakage detection."""

from __future__ import annotations

from hg_runtime.heldout_external_evaluation.schemas import (
    TASK_STATUS_HELDOUT,
    HeldoutEvaluationError,
    reject_heldout_authority,
)


def validate_heldout_task(task: dict) -> list[str]:
    issues = []
    if not task.get("task_id"):
        issues.append("missing_task_id")
    if task.get("status") != TASK_STATUS_HELDOUT:
        issues.append("task_must_be_heldout")
    if task.get("leaked_to_curriculum"):
        issues.append("task_leaked_to_curriculum")
    reject_heldout_authority(task)
    return issues


def check_leakage(task_id: str, curriculum_ids: list[str]) -> bool:
    return task_id in curriculum_ids


def validate_attempt(attempt: dict) -> list[str]:
    issues = []
    if not attempt.get("attempt_id"):
        issues.append("missing_attempt_id")
    if attempt.get("is_competence"):
        issues.append("must_not_claim_competence")
    if attempt.get("live_external_call"):
        issues.append("live_call_forbidden")
    reject_heldout_authority(attempt)
    return issues
