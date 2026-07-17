"""ORP-2 promotion request eligibility checks."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash

BLOCKED_STATUSES = {
    "REJECT_SOURCE": "REJECTED_SOURCE_BLOCKS_PROMOTION",
    "DEFER_REVIEW": "DEFERRED_REVIEW_BLOCKS_PROMOTION",
    "REQUEST_MORE_EVIDENCE": "MORE_EVIDENCE_REQUIRED_BLOCKS_PROMOTION",
    "QUARANTINE_RECOMMENDED": "QUARANTINE_RECOMMENDATION_BLOCKS_PROMOTION",
    "RETRACTION_RECOMMENDED": "RETRACTION_RECOMMENDATION_BLOCKS_PROMOTION",
}


def build_eligibility_record(*, eligibility_id: str, decision: dict, receipt_present: bool = True, provenance_present: bool = True) -> dict:
    reasons: list[str] = []
    if decision["decision_status"] != "APPROVE_FOR_PROVISIONAL_USE":
        reasons.append(BLOCKED_STATUSES[decision["decision_status"]])
    if not receipt_present:
        reasons.append("MISSING_RECEIPT_BLOCKS_PROMOTION")
    if not provenance_present:
        reasons.append("MISSING_PROVENANCE_BLOCKS_PROMOTION")
    record = {
        "schema_version": "1",
        "record_type": "promotion_eligibility_record_v1",
        "eligibility_id": eligibility_id,
        "decision_id": decision["decision_id"],
        "decision_hash": decision["decision_hash"],
        "decision_status": decision["decision_status"],
        "eligible_for_promotion_request": not reasons,
        "block_reasons": reasons,
        "receipt_present": receipt_present,
        "provenance_present": provenance_present,
        "eligible_is_truth": False,
        "promotion_request_is_promotion": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_blocked_promotion_record(*, blocked_id: str, source_id: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "blocked_promotion_record_v1",
        "blocked_promotion_id": blocked_id,
        "source_id": source_id,
        "block_reason": reason,
        "blocked_is_deletion": False,
        "promotion_request_created": False,
        "belief_mutated": False,
        "old_proof_mutated": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_context_blockers() -> list[dict]:
    reasons = [
        "HIGH_FEVER_BLOCKS_PROMOTION",
        "REDACTION_FAILURE_BLOCKS_PROMOTION",
        "SECURITY_FINDING_BLOCKS_PROMOTION",
        "MISSING_RECEIPT_BLOCKS_PROMOTION",
        "MISSING_PROVENANCE_BLOCKS_PROMOTION",
    ]
    return [
        build_blocked_promotion_record(blocked_id=f"orp2-context-block-{i:03d}", source_id=f"context-{i:03d}", reason=reason)
        for i, reason in enumerate(reasons, start=1)
    ]
