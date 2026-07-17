"""AEC-04 / CAGI-51 artifact writer — builds proposal receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.experiment_proposal.generator import (
    rank_proposals,
    validate_proposal,
    validate_review,
)
from hg_runtime.experiment_proposal.schemas import (
    PRIORITY_IS_NOT_URGENCY,
    PROPOSAL_IS_NOT_APPROVAL,
    REVIEW_IS_NOT_DECISION,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_proposal_artifacts(
    proposals: list[dict],
    reviews: list[dict],
) -> dict:
    validated = []
    for p in proposals:
        issues = validate_proposal(p)
        validated.append({"proposal": p, "valid": not issues, "issues": issues})

    validated_reviews = []
    for r in reviews:
        issues = validate_review(r)
        validated_reviews.append({"review": r, "valid": not issues, "issues": issues})

    ranked = rank_proposals(proposals)

    artifacts = {
        "proposals": validated,
        "proposal_count": len(validated),
        "reviews": validated_reviews,
        "review_count": len(validated_reviews),
        "ranked_order": [p["proposal_id"] for p in ranked],
        "all_proposals_draft": all(v["valid"] for v in validated),
        "all_reviews_not_decision": all(v["valid"] for v in validated_reviews),
        "no_approvals_granted": all(not p.get("approved_for_execution") for p in proposals),
        "boundary_assertions": {
            "proposal_is_not_approval": PROPOSAL_IS_NOT_APPROVAL,
            "review_is_not_decision": REVIEW_IS_NOT_DECISION,
            "priority_is_not_urgency": PRIORITY_IS_NOT_URGENCY,
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
