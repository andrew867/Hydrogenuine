"""Evidence promotion request records."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_evidence_promotion_request(*, request_id: str, decision: dict) -> dict:
    request = {
        "schema_version": "1",
        "record_type": "evidence_promotion_request_v1",
        "promotion_request_id": request_id,
        "decision_id": decision["decision_id"],
        "decision_hash": decision["decision_hash"],
        "target_record_id": decision["target_record_id"],
        "target_record_hash": decision["target_record_hash"],
        "requested_use": "PROVISIONAL_LOCAL_BELIEF_REVISION_INPUT",
        "promotion_request_is_promotion": False,
        "eligible_status_required": "APPROVE_FOR_PROVISIONAL_USE",
        "decision_status": decision["decision_status"],
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        **neutral_flags(),
    }
    request["request_hash"] = record_hash(request)
    assert_neutral(request)
    return request
