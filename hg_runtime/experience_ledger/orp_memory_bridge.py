"""P26-3 bridge from memory records to ORP-style promotion requests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.recall_index import build_recall_index
from hg_runtime.experience_ledger.schemas import assert_neutral, neutral_flags


def build_memory_promotion_request(memory: dict, *, request_id: str | None = None) -> dict:
    if not memory.get("provenance_refs"):
        return build_memory_promotion_rejection(
            memory_id=memory.get("memory_id", "UNKNOWN"),
            reason="MISSING_PROVENANCE",
            source="request_builder",
        )
    request = {
        "record_type": "memory_promotion_request_v1",
        "schema_version": "1",
        "request_id": request_id or f"p26-3-request-{memory['memory_id']}",
        "memory_id": memory["memory_id"],
        "memory_hash": memory["memory_hash"],
        "experience_id": memory["experience_id"],
        "provenance_refs": memory["provenance_refs"],
        "source_quality_refs": memory["source_quality_refs"],
        "request_status": "REQUESTED_ORP_REVIEW",
        "operator_orp_decision_required": True,
        "promotion_request_is_promotion": False,
        "approved_for_review_is_truth": False,
        **neutral_flags(),
    }
    with_hash(request, "request_hash")
    assert_neutral(request)
    return request


def build_memory_promotion_rejection(*, memory_id: str, reason: str, source: str) -> dict:
    rejection = {
        "record_type": "memory_promotion_rejection_v1",
        "schema_version": "1",
        "rejection_id": f"p26-3-reject-{memory_id}-{reason.lower()}",
        "memory_id": memory_id,
        "rejection_reason": reason,
        "rejection_source": source,
        "rejection_is_deletion": False,
        **neutral_flags(),
    }
    with_hash(rejection, "decision_hash")
    assert_neutral(rejection)
    return rejection


def build_orp_memory_bridge(repo_root: Path) -> dict:
    index = build_recall_index(repo_root)
    memories = index["memory_records"]
    requests = [build_memory_promotion_request(memory) for memory in memories]
    return {"recall_index": index, "memory_records": memories, "requests": requests}
