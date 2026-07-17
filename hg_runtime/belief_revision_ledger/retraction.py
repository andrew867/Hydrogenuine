"""Retraction records.

Retraction is append-only. It never deletes or rewrites the original claim; the
original claim is preserved and a new belief state supersedes the old one. A
retraction claims no truth.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.schemas import (
    RETRACTION_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_retraction_record(
    *,
    claim_id: str,
    previous_belief_state_id: str,
    new_belief_state_id: str,
    triggering_evidence_receipt_ids: list[str],
    reason: str,
) -> dict:
    record = {
        "schema": RETRACTION_RECORD_SCHEMA,
        "retraction_id": f"retraction-{claim_id}",
        "claim_id": claim_id,
        "previous_belief_state_id": previous_belief_state_id,
        "new_belief_state_id": new_belief_state_id,
        "triggering_evidence_receipt_ids": sorted(triggering_evidence_receipt_ids),
        "retraction_reason": reason,
        "original_claim_preserved": True,
        "deletion_performed": False,
        "rewrite_performed": False,
        "truth_claimed": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
