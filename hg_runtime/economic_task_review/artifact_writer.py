"""SIEW-02 / CAGI-64 artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.economic_task_review.reviewer import (
    has_defects,
    has_uncertainty,
    validate_review,
)
from hg_runtime.economic_task_review.schemas import (
    NO_LIVE_SUBMISSION,
    REVIEW_IS_NOT_CUSTOMER_ACCEPTANCE,
    REVIEW_IS_NOT_PAYMENT_PERMISSION,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_review_artifacts(reviews: list[dict], criteria: list[dict]) -> dict:
    validated = []
    for r in reviews:
        issues = validate_review(r)
        validated.append({
            "review": r,
            "valid": not issues,
            "issues": issues,
            "has_defects": has_defects(r),
            "has_uncertainty": has_uncertainty(r),
        })
    result = {
        "reviews": validated,
        "criteria": criteria,
        "review_count": len(validated),
        "all_reviews_valid": all(v["valid"] for v in validated),
        "no_customer_acceptance": all(not r.get("customer_accepted") for r in reviews),
        "no_payment_permission": all(not r.get("payment_permitted") for r in reviews),
        "all_require_operator_review": all(r.get("requires_operator_review") for r in reviews),
        "defect_count": sum(1 for v in validated if v["has_defects"]),
        "uncertainty_count": sum(1 for v in validated if v["has_uncertainty"]),
        "boundary_assertions": {
            "review_is_not_customer_acceptance": REVIEW_IS_NOT_CUSTOMER_ACCEPTANCE,
            "review_is_not_payment_permission": REVIEW_IS_NOT_PAYMENT_PERMISSION,
            "no_live_submission": NO_LIVE_SUBMISSION,
        },
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
