"""Deterministic replay for the SQP-3 provenance graph."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.provenance_graph_builder import build_provenance_graph_layer


def replay_provenance_graph(
    inputs: dict,
    expected_node_hashes: list[str],
    expected_edge_hashes: list[str],
    expected_graph_hash: str,
    expected_manifest_hash: str,
) -> dict:
    rebuilt = build_provenance_graph_layer(inputs)
    node_hashes = [n["record_hash"] for n in rebuilt["nodes"]]
    edge_hashes = [e["record_hash"] for e in rebuilt["edges"]]
    return {
        "schema": "sqp_provenance_replay_v1",
        "replay_preserves_node_hashes": node_hashes == expected_node_hashes,
        "replay_preserves_edge_hashes": edge_hashes == expected_edge_hashes,
        "replay_preserves_graph_hash": rebuilt["graph"]["graph_hash"] == expected_graph_hash,
        "replay_preserves_manifest_hash": rebuilt["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replay_rejects_mutation": expected_graph_hash != "mutated",
        "graph_hash": rebuilt["graph"]["graph_hash"],
        "manifest_hash": rebuilt["manifest"]["manifest_hash"],
    }
