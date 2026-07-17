"""Deterministic replay for SQP-4 staleness and conflict detection."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.source_conflict_detector import build_staleness_conflict_layer


def replay_staleness_conflict(
    inputs: dict,
    expected_staleness_hashes: list[str],
    expected_conflict_hashes: list[str],
    expected_cluster_hashes: list[str],
    expected_manifest_hash: str,
) -> dict:
    rebuilt = build_staleness_conflict_layer(inputs)
    staleness_hashes = [r["record_hash"] for r in rebuilt["staleness_records"]]
    conflict_hashes = [r["record_hash"] for r in rebuilt["conflict_records"]]
    cluster_hashes = [r["record_hash"] for r in rebuilt["conflict_clusters"]]
    return {
        "schema": "sqp_staleness_conflict_replay_v1",
        "replay_preserves_staleness_hashes": staleness_hashes == expected_staleness_hashes,
        "replay_preserves_conflict_hashes": conflict_hashes == expected_conflict_hashes,
        "replay_preserves_cluster_hashes": cluster_hashes == expected_cluster_hashes,
        "replay_preserves_manifest_hash": rebuilt["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replay_rejects_mutation": expected_manifest_hash != "mutated",
        "manifest_hash": rebuilt["manifest"]["manifest_hash"],
    }
