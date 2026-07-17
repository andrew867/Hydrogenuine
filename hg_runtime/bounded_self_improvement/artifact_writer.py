"""BSI-01 / CAGI-60 artifact writer — builds proposal receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.bounded_self_improvement.proposer import (
    link_evidence,
    validate_proposal,
    validate_queue,
)
from hg_runtime.bounded_self_improvement.schemas import (
    PROPOSAL_CANNOT_MUTATE_AUTHORITY,
    PROPOSAL_CANNOT_SELF_APPLY,
    PROPOSAL_IS_NOT_PATCH,
    PROPOSAL_IS_NOT_PERMISSION,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_proposal_artifacts(
    proposals: list[dict],
    queue: dict,
) -> dict:
    validated = []
    for p in proposals:
        issues = validate_proposal(p)
        evidence = link_evidence(p)
        validated.append({
            "proposal": p,
            "valid": not issues,
            "issues": issues,
            "evidence": evidence,
        })

    queue_issues = validate_queue(queue)

    artifacts = {
        "proposals": validated,
        "proposal_count": len(validated),
        "queue": queue,
        "queue_valid": not queue_issues,
        "queue_issues": queue_issues,
        "all_proposals_valid": all(v["valid"] for v in validated),
        "none_applied": queue.get("applied", 0) == 0,
        "all_require_operator_review": all(
            p.get("requires_operator_review") for p in proposals
        ),
        "boundary_assertions": {
            "proposal_is_not_patch": PROPOSAL_IS_NOT_PATCH,
            "proposal_is_not_permission": PROPOSAL_IS_NOT_PERMISSION,
            "proposal_cannot_self_apply": PROPOSAL_CANNOT_SELF_APPLY,
            "proposal_cannot_mutate_authority": PROPOSAL_CANNOT_MUTATE_AUTHORITY,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
