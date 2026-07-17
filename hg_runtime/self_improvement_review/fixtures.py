"""BSI-02 / CAGI-61 fixture data for self-improvement review."""

from __future__ import annotations

from hg_runtime.self_improvement_review.schemas import (
    RECOMMENDATION_SAFE,
    RECOMMENDATION_UNSAFE,
    REVIEW_STATUS_COMPLETED,
    REVIEW_STATUS_PENDING,
)


def fixture_review_records() -> list[dict]:
    return [
        {
            "review_id": "rev-001",
            "proposal_id": "prop-001",
            "status": REVIEW_STATUS_COMPLETED,
            "risk_classification": "LOW",
            "benefit_classification": "MODERATE",
            "recommendation": RECOMMENDATION_SAFE,
            "requires_operator_review": True,
            "approves_patch": False,
            "grants_permission": False,
        },
        {
            "review_id": "rev-002",
            "proposal_id": "prop-003",
            "status": REVIEW_STATUS_COMPLETED,
            "risk_classification": "MEDIUM",
            "benefit_classification": "HIGH",
            "recommendation": RECOMMENDATION_UNSAFE,
            "requires_operator_review": True,
            "approves_patch": False,
            "grants_permission": False,
        },
        {
            "review_id": "rev-003",
            "proposal_id": "prop-002",
            "status": REVIEW_STATUS_PENDING,
            "risk_classification": "LOW",
            "benefit_classification": "LOW",
            "recommendation": RECOMMENDATION_SAFE,
            "requires_operator_review": True,
            "approves_patch": False,
            "grants_permission": False,
        },
    ]


def fixture_evaluation_criteria() -> list[dict]:
    return [
        {"criterion_id": "crit-001", "name": "safety_impact", "weight": 0.4},
        {"criterion_id": "crit-002", "name": "coverage_benefit", "weight": 0.3},
        {"criterion_id": "crit-003", "name": "implementation_risk", "weight": 0.3},
    ]


def fixture_review_authority_attempt() -> dict:
    return {
        "review_id": "rev-bad",
        "approves_patch": True,
        "grants_permission": True,
        "self_approves": True,
        "mutates_policy": True,
        "bypasses_operator_review": True,
    }
