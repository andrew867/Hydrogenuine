"""BSI-02 / CAGI-61 reviewer — evaluates improvement proposals."""

from __future__ import annotations

from hg_runtime.self_improvement_review.schemas import (
    REVIEW_STATUS_COMPLETED,
    SelfImprovementReviewError,
    reject_review_authority,
)


def validate_review(review: dict) -> list[str]:
    issues = []
    if not review.get("review_id"):
        issues.append("missing_review_id")
    if not review.get("proposal_id"):
        issues.append("missing_proposal_id")
    if review.get("approves_patch"):
        issues.append("must_not_approve_patch")
    if review.get("grants_permission"):
        issues.append("must_not_grant_permission")
    if not review.get("requires_operator_review"):
        issues.append("must_require_operator_review")
    reject_review_authority(review)
    return issues


def classify_risk(review: dict) -> str:
    return review.get("risk_classification", "UNKNOWN")


def classify_benefit(review: dict) -> str:
    return review.get("benefit_classification", "UNKNOWN")


def requires_operator_escalation(review: dict) -> bool:
    return review.get("risk_classification") in ("MEDIUM", "HIGH", "CRITICAL")
