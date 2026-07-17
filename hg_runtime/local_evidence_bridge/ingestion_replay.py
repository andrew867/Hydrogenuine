"""LEB-1 ingestion replay."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import neutral_flags, record_hash


def replay_ingestion(receipts: list[dict], excerpts: list[dict], redactions: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [r["receipt_hash"] for r in receipts] != manifest.get("receipt_hashes", []):
        failures.append("receipt_hash_list_mismatch")
    if [r["receipt_hash"] for r in excerpts] != manifest.get("excerpt_hashes", []):
        failures.append("excerpt_hash_list_mismatch")
    if [r["record_hash"] for r in redactions] != manifest.get("redaction_hashes", []):
        failures.append("redaction_hash_list_mismatch")
    for receipt in receipts + excerpts:
        expected = record_hash({k: v for k, v in receipt.items() if k != "receipt_hash"})
        if receipt["receipt_hash"] != expected:
            failures.append(f"receipt_hash_mismatch:{receipt.get('receipt_id') or receipt.get('excerpt_id')}")
    return {
        "schema_version": "1",
        "record_type": "text_evidence_ingestion_replay_v1",
        "replay_id": "leb1-text-ingestion-replay",
        "replay_preserves_ingestion_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }
