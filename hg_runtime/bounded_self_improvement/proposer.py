"""BSI-01 / CAGI-60 proposer — creates and validates improvement proposals."""

from __future__ import annotations

from hg_runtime.bounded_self_improvement.schemas import (
    PROPOSAL_CATEGORIES,
    BoundedSelfImprovementError,
    reject_proposal_authority,
)


def validate_proposal(proposal: dict) -> list[str]:
    issues = []
    if not proposal.get("proposal_id"):
        issues.append("missing_proposal_id")
    if proposal.get("category") not in PROPOSAL_CATEGORIES:
        issues.append("invalid_category")
    if not proposal.get("target_component"):
        issues.append("missing_target_component")
    if not proposal.get("summary"):
        issues.append("missing_summary")
    if proposal.get("self_apply"):
        issues.append("self_apply_forbidden")
    if proposal.get("apply_patch"):
        issues.append("apply_patch_forbidden")
    if not proposal.get("requires_operator_review"):
        issues.append("must_require_operator_review")
    reject_proposal_authority(proposal)
    return issues


def validate_queue(queue: dict) -> list[str]:
    issues = []
    if not queue.get("queue_id"):
        issues.append("missing_queue_id")
    if queue.get("applied", 0) > 0:
        issues.append("no_proposals_may_be_applied")
    if queue.get("self_apply"):
        issues.append("queue_self_apply_forbidden")
    return issues


def link_evidence(proposal: dict) -> dict:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "evidence_links": proposal.get("evidence_links", []),
        "risk_level": proposal.get("risk_level", "UNKNOWN"),
        "linked": bool(proposal.get("evidence_links")),
    }
