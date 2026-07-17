"""Replay EWP-1 claim packet building for determinism checks."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.claim_packet_builder import (
    build_claim_evidence_packets,
    build_ewp1_inputs,
)
from hg_runtime.evidence_workbench_packets.schemas import record_hash


def replay_claim_packet_build(
    *,
    expected_manifest_hash: str,
    expected_packet_hashes: list[str],
) -> dict:
    inputs = build_ewp1_inputs()
    records = build_claim_evidence_packets(inputs)
    manifest_hash = record_hash(
        {
            "claim_packets": records["claim_evidence_packets"],
            "summaries": records["packet_source_summaries"],
            "supports": records["packet_support_records"],
            "contradictions": records["packet_contradiction_records"],
        }
    )
    packet_hashes = [row["packet_hash"] for row in records["claim_evidence_packets"]]
    return {
        "replay_preserves_packet_hashes": packet_hashes == expected_packet_hashes,
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "manifest_hash": manifest_hash,
        "packet_hashes": packet_hashes,
    }
