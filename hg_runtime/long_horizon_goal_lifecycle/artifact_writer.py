"""LHRE-01 / CAGI-54 artifact writer — builds goal lifecycle receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.long_horizon_goal_lifecycle.lifecycle import (
    decompose_goal,
    validate_checkpoint,
    validate_goal,
    validate_pause_resume,
)
from hg_runtime.long_horizon_goal_lifecycle.schemas import (
    CHECKPOINT_IS_NOT_AUTHORIZATION,
    GOAL_PLAN_IS_NOT_PERMISSION,
    GOAL_PROGRESS_IS_NOT_SUCCESS,
    MILESTONE_IS_NOT_DEPLOYMENT,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_goal_lifecycle_artifacts(
    goals: list[dict],
    milestones: list[dict],
    checkpoints: list[dict],
    pause_resume_records: list[dict],
) -> dict:
    validated_goals = []
    for g in goals:
        issues = validate_goal(g)
        decomp = decompose_goal(g, milestones)
        validated_goals.append({"goal": g, "valid": not issues, "issues": issues, "decomposition": decomp})

    validated_checkpoints = []
    for cp in checkpoints:
        issues = validate_checkpoint(cp)
        validated_checkpoints.append({"checkpoint": cp, "valid": not issues, "issues": issues})

    validated_pr = []
    for pr in pause_resume_records:
        issues = validate_pause_resume(pr)
        validated_pr.append({"record": pr, "valid": not issues, "issues": issues})

    artifacts = {
        "goals": validated_goals,
        "goal_count": len(validated_goals),
        "milestones": milestones,
        "milestone_count": len(milestones),
        "checkpoints": validated_checkpoints,
        "checkpoint_count": len(validated_checkpoints),
        "pause_resume_records": validated_pr,
        "pause_resume_count": len(validated_pr),
        "all_goals_valid": all(v["valid"] for v in validated_goals),
        "all_checkpoints_valid": all(v["valid"] for v in validated_checkpoints),
        "no_deployment_claims": all(not m.get("is_deployment") for m in milestones),
        "boundary_assertions": {
            "goal_progress_is_not_success": GOAL_PROGRESS_IS_NOT_SUCCESS,
            "goal_plan_is_not_permission": GOAL_PLAN_IS_NOT_PERMISSION,
            "milestone_is_not_deployment": MILESTONE_IS_NOT_DEPLOYMENT,
            "checkpoint_is_not_authorization": CHECKPOINT_IS_NOT_AUTHORIZATION,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    hits = []
    for pattern in ("sk-", "api_key=", "Bearer ", "token=", "password="):
        if pattern.lower() in text.lower():
            hits.append(pattern)
    return hits
