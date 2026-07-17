"""LEB-7 evidence retraction records (append-only).

An evidence retraction is not erasure: the original receipt is preserved, derived
belief revisions remain auditable, and a retraction creates a review requirement.
No truth is claimed.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

VALID_REASONS = ("BAD", "SUSPECT", "STALE", "CONTRADICTED", "REDACTION_FAILED")


def build_evidence_retraction_record(*, retraction_id: str, receipt: dict, reason: str) -> dict:
    if reason not in VALID_REASONS:
        raise EvidenceBridgeError(f"invalid_retraction_reason:{reason}")
    record = {
        "schema_version": "1",
        "record_type": "evidence_retraction_record_v1",
        "retraction_id": retraction_id,
        "original_ref": receipt.get("receipt_id", "unknown"),
        "original_receipt_hash": receipt.get("receipt_hash", ""),
        "reason": reason,
        "review_task_id": f"rrt-{retraction_id}",
        "evidence_retraction_is_erasure": False,
        "original_receipt_preserved": True,
        "deletion_performed": False,
        "rewrite_performed": False,
        "review_required": True,
        "derived_belief_revisions_auditable": True,
        "truth_claimed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
