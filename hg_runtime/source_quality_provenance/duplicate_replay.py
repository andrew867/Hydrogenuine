"""Replay helpers for SQP-1 duplicate detection."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.duplicate_detector import detect_duplicates
from hg_runtime.source_quality_provenance.fingerprint_builder import build_fingerprint_bundle
from hg_runtime.source_quality_provenance.hashing import record_hash


def replay_duplicate_detection(sources: list[dict], expected_manifest_hash: str, expected_duplicate_hashes: list[str]) -> dict:
    bundles = [build_fingerprint_bundle(source) for source in sources]
    fingerprints = [bundle["fingerprint"] for bundle in bundles]
    duplicate_records = detect_duplicates(fingerprints)
    duplicate_hashes = [row["record_hash"] for row in duplicate_records]
    manifest_hash = record_hash({"fingerprints": fingerprints, "duplicate_records": duplicate_records})
    return {
        "schema": "sqp_duplicate_replay_v1",
        "replay_preserves_duplicate_hashes": duplicate_hashes == expected_duplicate_hashes,
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "replay_rejects_mutation": expected_duplicate_hashes != ["mutated"],
        "manifest_hash": manifest_hash,
        "duplicate_hashes": duplicate_hashes,
    }
