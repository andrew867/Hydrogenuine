"""LEB-2 candidate contradiction records."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import assert_neutral, neutral_flags, record_hash


def build_contradiction_record(*, link_id: str, receipt: dict, claim_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "evidence_contradiction_record_v1",
        "contradiction_record_id": f"contradiction-{link_id}",
        "link_id": link_id,
        "claim_id": claim_id,
        "evidence_receipt_id": receipt["receipt_id"],
        "evidence_receipt_hash": receipt["receipt_hash"],
        "contradiction_status": "CANDIDATE_CONTRADICTION_REVIEW_REQUIRED",
        "contradiction_link_is_not_truth_resolution": True,
        "evidence_receipt_is_not_automatic_belief_revision": True,
        "reviewable_input_only": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
