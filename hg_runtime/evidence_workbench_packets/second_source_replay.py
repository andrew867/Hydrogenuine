"""Replay EWP-2 second-source gate for determinism checks."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import record_hash
from hg_runtime.evidence_workbench_packets.second_source_gate import build_second_source_gate_layer


def replay_second_source_gate(
    *,
    expected_manifest_hash: str,
    expected_result_hashes: list[str],
) -> dict:
    records = build_second_source_gate_layer()
    manifest_hash = record_hash(
        {
            "requirements": records["packet_second_source_requirements"],
            "results": records["packet_second_source_results"],
        }
    )
    result_hashes = [row["record_hash"] for row in records["packet_second_source_results"]]
    return {
        "replay_preserves_result_hashes": result_hashes == expected_result_hashes,
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "manifest_hash": manifest_hash,
        "result_hashes": result_hashes,
    }
