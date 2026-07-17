"""Operator review decision records."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.operator_review_queue.schemas import REVIEW_DECISION_SCHEMA, neutral_flags


def review_decision(queue_item: dict, result: str) -> dict:
    row = {
        "schema": REVIEW_DECISION_SCHEMA,
        "decision_id": "decision-" + queue_item["source_patch_candidate_id"].lower(),
        "queue_item_id": queue_item["queue_item_id"],
        "source_patch_candidate_id": queue_item["source_patch_candidate_id"],
        "decision": result,
        "queue_entry_is_approval": False,
        **neutral_flags(),
    }
    row["decision_hash"] = canonical_hash(row)
    return row
