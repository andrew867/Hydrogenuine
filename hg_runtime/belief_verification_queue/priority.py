"""Deterministic verification priority assignment.

Priority is a pure function of conflict type and the number of distinct source
receipts. It introduces no randomness and no time dependence, so replay is exact.
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.schemas import (
    VERIFICATION_PRIORITY_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

CONFLICT_WEIGHT = {
    "UNSOURCED_CONSENSUS": 90,
    "FACTUAL_DIVERGENCE": 80,
    "MORAL_CONFLICT": 60,
    "OMISSION_DIVERGENCE": 50,
    "REFUSAL_DIVERGENCE": 40,
    "FRAMING_DIVERGENCE": 30,
}


def compute_priority(conflict: dict) -> int:
    base = CONFLICT_WEIGHT.get(conflict.get("conflict_type"), 20)
    # More distinct source receipts -> slightly higher priority, deterministically.
    breadth = min(len(conflict.get("source_receipt_ids", [])), 5)
    return base + breadth


def build_priority_record(conflict: dict) -> dict:
    record = {
        "schema": VERIFICATION_PRIORITY_RECORD_SCHEMA,
        "conflict_id": conflict["conflict_id"],
        "conflict_type": conflict["conflict_type"],
        "priority": compute_priority(conflict),
        "deterministic": True,
        "source_receipt_count": len(conflict.get("source_receipt_ids", [])),
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
