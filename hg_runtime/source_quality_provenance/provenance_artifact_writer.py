"""Artifact writer for the SQP-3 provenance graph."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_provenance_artifacts(
    *,
    proof_dir: Path,
    nodes: list[dict],
    edges: list[dict],
    graph: dict,
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "provenance_nodes.jsonl", nodes)
    write_jsonl(proof_dir / "provenance_edges.jsonl", edges)
    write_json(proof_dir / "provenance_graph.json", graph)
    write_json(proof_dir / "provenance_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", nodes + edges)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
