"""BSI-02 / CAGI-61 artifact writer — builds review receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.self_improvement_review.reviewer import (
    classify_benefit,
    classify_risk,
    requires_operator_escalation,
    validate_review,
)
from hg_runtime.self_improvement_review.schemas import (
    REVIEW_CANNOT_AUTHORIZE_TOOLS,
    REVIEW_CANNOT_MUTATE_POLICY,
    REVIEW_PASS_IS_NOT_PATCH_APPROVAL,
    REVIEW_PASS_IS_NOT_PERMISSION,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_review_artifacts(
    reviews: list[dict],
    criteria: list[dict],
) -> dict:
    validated = []
    for r in reviews:
        issues = validate_review(r)
        validated.append({
            "review": r,
            "valid": not issues,
            "issues": issues,
            "risk": classify_risk(r),
            "benefit": classify_benefit(r),
            "escalation_needed": requires_operator_escalation(r),
        })

    artifacts = {
        "reviews": validated,
        "review_count": len(validated),
        "criteria": criteria,
        "all_reviews_valid": all(v["valid"] for v in validated),
        "all_require_operator_review": all(
            r.get("requires_operator_review") for r in reviews
        ),
        "none_approve_patch": all(not r.get("approves_patch") for r in reviews),
        "escalations_needed": sum(1 for v in validated if v["escalation_needed"]),
        "boundary_assertions": {
            "review_pass_is_not_permission": REVIEW_PASS_IS_NOT_PERMISSION,
            "review_pass_is_not_patch_approval": REVIEW_PASS_IS_NOT_PATCH_APPROVAL,
            "review_cannot_authorize_tools": REVIEW_CANNOT_AUTHORIZE_TOOLS,
            "review_cannot_mutate_policy": REVIEW_CANNOT_MUTATE_POLICY,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
