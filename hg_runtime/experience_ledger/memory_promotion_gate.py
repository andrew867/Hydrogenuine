"""P26-3 memory promotion gate."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.orp_memory_bridge import build_memory_promotion_rejection
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError, assert_neutral, neutral_flags

DECISION_STATUSES = {
    "APPROVED_FOR_REVIEW",
    "REJECTED",
    "DEFERRED",
    "REVIEW_ONLY_QUARANTINED",
}


def decide_memory_promotion(request: dict, status: str) -> dict:
    if status not in DECISION_STATUSES:
        raise ExperienceLedgerBoundaryError(f"unknown_decision:{status}")
    if request.get("record_type") == "memory_promotion_rejection_v1":
        return request
    if request.get("promotion_request_auto_applied"):
        raise ExperienceLedgerBoundaryError("automatic_promotion_forbidden")
    if request.get("memory_treated_as_truth"):
        raise ExperienceLedgerBoundaryError("memory_truth_forbidden")
    if request.get("recall_treated_as_authority"):
        raise ExperienceLedgerBoundaryError("recall_authority_forbidden")
    if not request.get("provenance_refs"):
        return build_memory_promotion_rejection(
            memory_id=request.get("memory_id", "UNKNOWN"),
            reason="MISSING_PROVENANCE",
            source="promotion_gate",
        )
    decision = {
        "record_type": "memory_promotion_decision_v1",
        "schema_version": "1",
        "decision_id": f"p26-3-decision-{request['memory_id']}-{status.lower()}",
        "request_id": request["request_id"],
        "memory_id": request["memory_id"],
        "decision_status": status,
        "operator_orp_decision_recorded": True,
        "approved_for_review_without_truth_claim": status == "APPROVED_FOR_REVIEW",
        "review_only": status in {"APPROVED_FOR_REVIEW", "REVIEW_ONLY_QUARANTINED"},
        "promotion_request_is_promotion": False,
        "operator_review_treated_as_truth": False,
        **neutral_flags(),
    }
    with_hash(decision, "decision_hash")
    assert_neutral(decision)
    return decision
