"""AEC-04 / CAGI-51 proposal generator — creates and validates experiment proposals."""

from __future__ import annotations

from hg_runtime.experiment_proposal.schemas import (
    PROPOSAL_STATUS_DRAFT,
    REVIEW_STATUS_NOT_DECISION,
    ExperimentProposalError,
    reject_live_proposal,
)


def validate_proposal(proposal: dict) -> list[str]:
    issues = []
    if not proposal.get("proposal_id"):
        issues.append("missing_proposal_id")
    if not proposal.get("type"):
        issues.append("missing_type")
    if not proposal.get("hypothesis_ref"):
        issues.append("missing_hypothesis_ref")
    if proposal.get("status") != PROPOSAL_STATUS_DRAFT:
        issues.append("proposal_must_be_draft")
    if proposal.get("approved_for_execution"):
        issues.append("must_not_be_approved")
    reject_live_proposal(proposal)
    return issues


def validate_review(review: dict) -> list[str]:
    issues = []
    if not review.get("proposal_id"):
        issues.append("missing_proposal_id")
    if review.get("status") != REVIEW_STATUS_NOT_DECISION:
        issues.append("review_must_not_be_decision")
    if review.get("is_approval"):
        issues.append("review_must_not_approve")
    return issues


def rank_proposals(proposals: list[dict]) -> list[dict]:
    priority_order = {"CRITICAL_SAFETY": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(proposals, key=lambda p: priority_order.get(p.get("priority", "LOW"), 99))
