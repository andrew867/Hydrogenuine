"""Contradiction records.

When supporting and contradicting evidence collide, a contradiction record is
created. A contradiction does not resolve truth; it opens a revision/retraction
path so the conflict is never hidden.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.schemas import (
    CONTRADICTION_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_contradiction_record(
    *,
    claim_id: str,
    supporting_ids: list[str],
    contradicting_ids: list[str],
    status: str,
) -> dict:
    record = {
        "schema": CONTRADICTION_RECORD_SCHEMA,
        "contradiction_id": f"contradiction-{claim_id}",
        "claim_id": claim_id,
        "supporting_evidence_receipt_ids": sorted(supporting_ids),
        "contradicting_evidence_receipt_ids": sorted(contradicting_ids),
        "contradiction_status": status,
        "truth_resolved": False,
        "contradictions_resolve_truth": False,
        "authority_granted": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
