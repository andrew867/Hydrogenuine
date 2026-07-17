"""Phase 25 advisory risk classifier.

Assigns a descriptive risk level to each proposal. Risk is advisory: a HIGH risk
does not block by authority, and a LOW risk does not grant permission. Every
non-trivial proposal routes to operator review.
"""

from __future__ import annotations

from hg_runtime.advisory_self_improvement.schemas import (
    RISK_LEVELS,
    Phase25BoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

_RISK_BY_CATEGORY = {
    "DOCUMENTATION": "LOW",
    "OBSERVABILITY": "LOW",
    "TEST_HARDENING": "MEDIUM",
    "COVERAGE_EXPANSION": "MEDIUM",
    "OPERATOR_WORKFLOW": "MEDIUM",
    "GAP_RECONCILIATION": "REQUIRES_OPERATOR_REVIEW",
}


def risk_for_category(category: str) -> str:
    return _RISK_BY_CATEGORY.get(category, "REQUIRES_OPERATOR_REVIEW")


def build_risk_record(*, proposal_id: str, category: str) -> dict:
    risk_level = risk_for_category(category)
    if risk_level not in RISK_LEVELS:
        raise Phase25BoundaryError(f"unknown_risk_level:{risk_level}")
    record = {
        "schema_version": "1",
        "record_type": "advisory_risk_record_v1",
        "proposal_id": proposal_id,
        "category": category,
        "risk_level": risk_level,
        "doctrine_note": "Risk is advisory; it neither blocks by authority nor grants permission.",
        "risk_authorizes_action": False,
        "risk_is_truth": False,
        "advisory_output_is_authority": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def classify_risks(proposals: list[dict]) -> list[dict]:
    return [build_risk_record(proposal_id=p["proposal_id"], category=p["category"]) for p in proposals]
