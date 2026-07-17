"""SIEW-02 / CAGI-64 reviewer — reviews simulated work products."""

from __future__ import annotations

from hg_runtime.economic_task_review.schemas import (
    EconomicTaskReviewError,
    reject_real_acceptance,
)


def validate_review(review: dict) -> list[str]:
    issues = []
    if not review.get("review_id"):
        issues.append("missing_review_id")
    if not review.get("task_id"):
        issues.append("missing_task_id")
    if review.get("customer_accepted"):
        issues.append("customer_acceptance_forbidden")
    if review.get("payment_permitted"):
        issues.append("payment_permission_forbidden")
    if not review.get("requires_operator_review"):
        issues.append("must_require_operator_review")
    reject_real_acceptance(review)
    return issues


def has_defects(review: dict) -> bool:
    return bool(review.get("defects"))


def has_uncertainty(review: dict) -> bool:
    return review.get("uncertainty") is not None
