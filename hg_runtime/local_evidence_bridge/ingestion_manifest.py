"""LEB-1 ingestion manifest."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_ingestion_manifest(paths: list[str], receipts: list[dict], excerpts: list[dict], redactions: list[dict]) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "text_evidence_ingestion_manifest_v1",
        "manifest_id": "leb1-text-evidence-ingestion",
        "explicit_source_paths": paths,
        "source_count": len(paths),
        "evidence_receipt_count": len(receipts),
        "excerpt_receipt_count": len(excerpts),
        "redaction_record_count": len(redactions),
        "receipt_hashes": [r["receipt_hash"] for r in receipts],
        "excerpt_hashes": [r["receipt_hash"] for r in excerpts],
        "redaction_hashes": [r["record_hash"] for r in redactions],
        "only_explicit_paths": True,
        "approved_fixture_paths_only": True,
        "operator_inbox_disabled_by_default": True,
        "no_belief_promotion": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
