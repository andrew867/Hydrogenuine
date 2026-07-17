"""LEB-6 evidence quarantine hooks.

Produces quarantine *candidate* metadata records for suspicious local evidence
receipts. A quarantine candidate is not deletion: the original receipt is
preserved and a review task is required. Nothing is deleted or rewritten.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)


def _is_suspicious(receipt: dict) -> bool:
    return bool(receipt.get("secret_like_content_redacted"))


def build_evidence_quarantine_candidate(*, candidate_id: str, receipt: dict, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "evidence_quarantine_candidate_v1",
        "quarantine_candidate_id": candidate_id,
        "original_ref": receipt.get("receipt_id", "unknown"),
        "content_hash": receipt.get("receipt_hash", ""),
        "reason": reason,
        "review_task_id": f"qrt-{candidate_id}",
        "quarantine_candidate_is_deletion": False,
        "original_preserved": True,
        "deletion_performed": False,
        "rewrite_performed": False,
        "auto_quarantine_enforced": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_evidence_quarantine_candidates(receipts: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for i, r in enumerate(sorted(receipts, key=lambda x: x.get("receipt_id", "")), start=1):
        if _is_suspicious(r):
            candidates.append(
                build_evidence_quarantine_candidate(
                    candidate_id=f"evq-{i:03d}", receipt=r, reason="redaction_flagged_suspicious"
                )
            )
    return candidates
