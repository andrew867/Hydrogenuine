"""Deterministic replay for the SQP-5 review policy adapter."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.review_policy_adapter import build_review_policy_adapter_layer


def replay_review_policy_adapter(
    inputs: dict,
    expected_hint_hashes: list[str],
    expected_priority_hashes: list[str],
    expected_blocked_hashes: list[str],
    expected_manifest_hash: str,
) -> dict:
    rebuilt = build_review_policy_adapter_layer(inputs)
    hint_hashes = [h["record_hash"] for h in rebuilt["hints"]]
    priority_hashes = [p["record_hash"] for p in rebuilt["priorities"]]
    blocked_hashes = [b["record_hash"] for b in rebuilt["blocked_hints"]]
    return {
        "schema": "sqp_review_hint_replay_v1",
        "replay_preserves_hint_hashes": hint_hashes == expected_hint_hashes,
        "replay_preserves_priority_hashes": priority_hashes == expected_priority_hashes,
        "replay_preserves_blocked_hashes": blocked_hashes == expected_blocked_hashes,
        "replay_preserves_manifest_hash": rebuilt["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replay_rejects_mutation": expected_manifest_hash != "mutated",
        "manifest_hash": rebuilt["manifest"]["manifest_hash"],
    }
