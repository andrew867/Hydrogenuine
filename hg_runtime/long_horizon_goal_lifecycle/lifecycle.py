"""LHRE-01 / CAGI-54 lifecycle engine — goal decomposition, checkpointing, pause/resume."""

from __future__ import annotations

from hg_runtime.long_horizon_goal_lifecycle.schemas import (
    CHECKPOINT_STATUS_SAVED,
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_PAUSED,
    GOAL_STATUS_RESUMED,
    MILESTONE_STATUS_PENDING,
    LongHorizonGoalError,
    reject_goal_authority,
)


def validate_goal(goal: dict) -> list[str]:
    issues = []
    if not goal.get("goal_id"):
        issues.append("missing_goal_id")
    if not goal.get("milestones"):
        issues.append("missing_milestones")
    if goal.get("authorizes_action"):
        issues.append("goal_must_not_authorize")
    if goal.get("deployment_ready"):
        issues.append("goal_must_not_claim_deployment")
    reject_goal_authority(goal)
    return issues


def decompose_goal(goal: dict, milestones: list[dict]) -> dict:
    goal_milestones = [m for m in milestones if m.get("goal_id") == goal["goal_id"]]
    return {
        "goal_id": goal["goal_id"],
        "milestone_count": len(goal_milestones),
        "all_pending": all(m.get("status") == MILESTONE_STATUS_PENDING for m in goal_milestones),
        "no_deployment_claims": all(not m.get("is_deployment") for m in goal_milestones),
    }


def validate_checkpoint(checkpoint: dict) -> list[str]:
    issues = []
    if not checkpoint.get("checkpoint_id"):
        issues.append("missing_checkpoint_id")
    if not checkpoint.get("state_hash"):
        issues.append("missing_state_hash")
    if checkpoint.get("authorizes_action"):
        issues.append("checkpoint_must_not_authorize")
    return issues


def detect_state_mutation(checkpoint: dict, current_hash: str) -> bool:
    return checkpoint.get("state_hash") != current_hash


def validate_pause_resume(record: dict) -> list[str]:
    issues = []
    if not record.get("record_id"):
        issues.append("missing_record_id")
    if record.get("action") not in ("PAUSE", "RESUME"):
        issues.append("invalid_action")
    if record.get("authorizes_action"):
        issues.append("resume_must_not_authorize")
    return issues
