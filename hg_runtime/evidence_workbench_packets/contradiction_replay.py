"""Replay EWP-3 contradiction packet building."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.contradiction_packet_builder import build_contradiction_review_layer
from hg_runtime.evidence_workbench_packets.schemas import record_hash


def replay_contradiction_packets(
    *,
    expected_manifest_hash: str,
    expected_packet_hashes: list[str],
) -> dict:
    records = build_contradiction_review_layer()
    manifest_hash = record_hash(
        {
            "packets": records["contradiction_review_packets"],
            "clusters": records["contradiction_cluster_packets"],
        }
    )
    packet_hashes = [row["packet_hash"] for row in records["contradiction_review_packets"]]
    return {
        "replay_preserves_packet_hashes": packet_hashes == expected_packet_hashes,
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "manifest_hash": manifest_hash,
        "packet_hashes": packet_hashes,
    }
