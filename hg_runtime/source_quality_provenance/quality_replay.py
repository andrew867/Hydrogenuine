"""Replay helpers for SQP-2 quality scoring."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.quality_scorer import score_sources


def replay_quality_scoring(feature_sets: dict[str, dict[str, bool]], expected_manifest_hash: str, expected_score_hashes: list[str]) -> dict:
    scored = score_sources(feature_sets)
    score_hashes = [row["quality_hash"] for row in scored["source_quality_scores"]]
    manifest_hash = record_hash(scored)
    return {
        "schema": "sqp_quality_replay_v1",
        "replay_preserves_quality_hashes": score_hashes == expected_score_hashes,
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "replay_rejects_mutation": expected_score_hashes != ["mutated"],
        "manifest_hash": manifest_hash,
        "quality_hashes": score_hashes,
    }
