"""LHRE-01 / CAGI-54 long-horizon goal lifecycle schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "LHRE-01"
LEGACY_PHASE_ID = "CAGI-54"
PARENT_PHASE_ID = "AEC-06"
PRECURSOR_PHASE_ID = "RUNTIME-P32"

VERDICT_GREEN = "GREEN_LHRE_01_LONG_HORIZON_GOAL_LIFECYCLE"
VERDICT_YELLOW = "YELLOW_LHRE_01_GOAL_LIFECYCLE_PARTIAL"
VERDICT_RED = "RED_LHRE_01_GOAL_LIFECYCLE_FAILED"
GATE_RESULT_SCHEMA = "lhre_01_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

GOAL_STATUS_ACTIVE = "ACTIVE_NOT_COMPLETE"
GOAL_STATUS_PAUSED = "PAUSED_NOT_ABANDONED"
GOAL_STATUS_RESUMED = "RESUMED_NOT_REAUTHORIZED"
MILESTONE_STATUS_PENDING = "PENDING_NOT_DEPLOYED"
CHECKPOINT_STATUS_SAVED = "CHECKPOINT_SAVED"

GOAL_PROGRESS_IS_NOT_SUCCESS = "Goal progress is not success."
GOAL_PLAN_IS_NOT_PERMISSION = "A goal plan is not permission to act."
MILESTONE_IS_NOT_DEPLOYMENT = "Milestone completion is not deployment readiness."
CHECKPOINT_IS_NOT_AUTHORIZATION = "A checkpoint is not authorization to continue."


class LongHorizonGoalError(Exception):
    pass


def reject_goal_authority(payload: dict) -> None:
    for key in (
        "authorizes_action",
        "grants_authority",
        "authorizes_tool",
        "creates_live_effect",
        "claims_agi",
        "deployment_ready",
        "goal_completion_is_success",
        "milestone_is_deployment",
    ):
        if payload.get(key):
            raise LongHorizonGoalError(
                f"Goal authority boundary violation: {key} must not be truthy"
            )
