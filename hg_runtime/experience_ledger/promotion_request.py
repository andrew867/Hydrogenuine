"""P26 memory promotion request and decision builders."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError, assert_neutral, neutral_flags


def build_memory_promotion_request(*, request_id: str, memory_record: dict) -> dict:
    if not memory_record.get("provenance_refs"):
        raise ExperienceLedgerBoundaryError("promotion_requires_provenance")
    request = {
        "record_type": "memory_promotion_request_v1",
        "schema_version": "1",
        "request_id": request_id,
        "memory_id": memory_record["memory_id"],
        "memory_hash": memory_record["memory_hash"],
        "provenance_refs": list(memory_record["provenance_refs"]),
        "operator_promotion_required": True,
        "orp_bridge_required": True,
        "promotion_request_is_promotion": False,
        "promotion_request_auto_applied": False,
        **neutral_flags(),
    }
    with_hash(request, "request_hash")
    assert_neutral(request)
    return request


def build_memory_promotion_decision(*, decision_id: str, request: dict, status: str = "DEFERRED_PENDING_ORP") -> dict:
    decision = {
        "record_type": "memory_promotion_decision_v1",
        "schema_version": "1",
        "decision_id": decision_id,
        "request_id": request["request_id"],
        "request_hash": request["request_hash"],
        "status": status,
        "operator_review_is_truth": False,
        "operator_review_treated_as_truth": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "orp_bypassed": False,
        **neutral_flags(),
    }
    with_hash(decision, "decision_hash")
    assert_neutral(decision)
    return decision

