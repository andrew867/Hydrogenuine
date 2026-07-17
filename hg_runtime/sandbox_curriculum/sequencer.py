"""AEC-02 / CAGI-49 curriculum sequencer — orders and validates task sequences."""

from __future__ import annotations

from hg_runtime.sandbox_curriculum.schemas import (
    SEQUENCE_STATUS_PROPOSED,
    TASK_STATUS_SANDBOX,
    SandboxCurriculumError,
    reject_live_curriculum,
)


def validate_task(task: dict) -> list[str]:
    issues = []
    if not task.get("task_id"):
        issues.append("missing_task_id")
    if not task.get("category"):
        issues.append("missing_category")
    if not task.get("difficulty"):
        issues.append("missing_difficulty")
    if task.get("status") != TASK_STATUS_SANDBOX:
        issues.append("task_must_be_sandbox")
    if task.get("live_execution_enabled"):
        issues.append("live_execution_forbidden")
    reject_live_curriculum(task)
    return issues


def validate_sequence(sequence: dict, task_ids: set[str]) -> list[str]:
    issues = []
    if not sequence.get("sequence_id"):
        issues.append("missing_sequence_id")
    if sequence.get("status") != SEQUENCE_STATUS_PROPOSED:
        issues.append("sequence_must_be_proposed")
    if not sequence.get("sandbox_only"):
        issues.append("sequence_must_be_sandbox_only")
    if sequence.get("deploy_to_production"):
        issues.append("deploy_forbidden")
    for tid in sequence.get("task_ids", []):
        if tid not in task_ids:
            issues.append(f"unknown_task_{tid}")
    reject_live_curriculum(sequence)
    return issues


def build_sequence_order(sequence: dict, tasks: list[dict]) -> list[dict]:
    task_map = {t["task_id"]: t for t in tasks}
    ordered = []
    for tid in sequence.get("task_ids", []):
        if tid in task_map:
            ordered.append(task_map[tid])
    return ordered


def score_curriculum(tasks: list[dict], scores: list[dict]) -> dict:
    score_map = {s["task_id"]: s for s in scores}
    total = 0.0
    count = 0
    for task in tasks:
        s = score_map.get(task["task_id"])
        if s:
            total += s["score"]
            count += 1
    return {
        "total_score": total,
        "task_count": count,
        "average": total / count if count else 0.0,
        "all_scores_not_truth": all(not s.get("is_truth") for s in scores),
    }
