"""LEB-0 source manifest."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_source_manifest(sources: list[dict], evidence_receipts: list[dict], excerpt_receipts: list[dict], boundary: dict) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "local_source_manifest_v1",
        "manifest_id": "leb0-local-source-manifest",
        "source_count": len(sources),
        "evidence_receipt_count": len(evidence_receipts),
        "excerpt_receipt_count": len(excerpt_receipts),
        "source_hashes": [s["record_hash"] for s in sources],
        "evidence_receipt_hashes": [r["receipt_hash"] for r in evidence_receipts],
        "excerpt_receipt_hashes": [r["receipt_hash"] for r in excerpt_receipts],
        "boundary_receipt_hash": boundary["receipt_hash"],
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
