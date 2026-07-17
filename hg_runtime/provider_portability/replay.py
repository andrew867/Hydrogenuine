"""Replay validation for Phase 42 receipts."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash


def replay_receipts(receipts: list[dict], expected_hashes: list[str] | None = None) -> dict:
    failures = []
    hashes = []
    for index, receipt in enumerate(receipts):
        copy = dict(receipt)
        receipt_hash = copy.pop("receipt_hash", None)
        expected = canonical_hash(copy)
        hashes.append(receipt_hash)
        if expected != receipt_hash:
            failures.append(f"receipt_hash_mismatch:{index}")
        if receipt.get("external_provider_call_made") or receipt.get("authority_granted") or receipt.get("tools_authorized"):
            failures.append(f"boundary_violation:{index}")
    if expected_hashes is not None and hashes != expected_hashes:
        failures.append("receipt_hash_list_mismatch")
    return {"ok": not failures, "failures": failures, "receipt_hashes": hashes, "receipt_count": len(receipts), "replay_hash": canonical_hash({"hashes": hashes})}
