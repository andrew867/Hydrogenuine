"""LEB-7 evidence decay records (append-only).

Evidence decay is not deletion. A decay record marks a stale receipt as decayed
while preserving the original; the receipt and any derived belief revisions remain
auditable.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_evidence_decay_record(*, decay_id: str, receipt: dict, retraction_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "evidence_decay_record_v1",
        "decay_id": decay_id,
        "original_ref": receipt.get("receipt_id", "unknown"),
        "original_receipt_hash": receipt.get("receipt_hash", ""),
        "reason": "STALE",
        "source_retraction_id": retraction_id,
        "evidence_decay_is_deletion": False,
        "evidence_decay_is_erasure": False,
        "original_receipt_preserved": True,
        "deletion_performed": False,
        "derived_belief_revisions_auditable": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
