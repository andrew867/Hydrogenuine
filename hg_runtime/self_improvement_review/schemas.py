"""BSI-02 / CAGI-61 self-improvement review schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "BSI-02"
LEGACY_PHASE_ID = "CAGI-61"
PARENT_PHASE_ID = "BSI-01"

VERDICT_GREEN = "GREEN_P61_SELF_IMPROVEMENT_REVIEW_EVALUATION"
VERDICT_YELLOW = "YELLOW_P61_SELF_IMPROVEMENT_REVIEW_PARTIAL"
VERDICT_RED = "RED_P61_SELF_IMPROVEMENT_REVIEW_FAILED"
GATE_RESULT_SCHEMA = "bsi_02_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

REVIEW_STATUS_PENDING = "REVIEW_PENDING"
REVIEW_STATUS_COMPLETED = "REVIEW_COMPLETED_NOT_APPROVED"
RECOMMENDATION_SAFE = "SAFE_FOR_OPERATOR_REVIEW"
RECOMMENDATION_UNSAFE = "UNSAFE_REQUIRES_ESCALATION"

REVIEW_PASS_IS_NOT_PERMISSION = "A review pass is not permission."
REVIEW_PASS_IS_NOT_PATCH_APPROVAL = "A review pass is not patch approval."
REVIEW_CANNOT_AUTHORIZE_TOOLS = "A review cannot authorize tools."
REVIEW_CANNOT_MUTATE_POLICY = "A review cannot mutate policy."


class SelfImprovementReviewError(Exception):
    pass


def reject_review_authority(payload: dict) -> None:
    for key in (
        "approves_patch",
        "grants_permission",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "mutates_policy",
        "mutates_gate",
        "bypasses_operator_review",
        "self_approves",
    ):
        if payload.get(key):
            raise SelfImprovementReviewError(
                f"Review authority boundary violation: {key} must not be truthy"
            )
