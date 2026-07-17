"""Artifact writer for EWP-3 contradiction review packets."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_contradiction_artifacts(
    *,
    proof_dir: Path,
    contradiction_review_packets: list[dict],
    contradiction_cluster_packets: list[dict],
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "contradiction_review_packets.jsonl", contradiction_review_packets)
    write_jsonl(proof_dir / "contradiction_cluster_packets.jsonl", contradiction_cluster_packets)
    write_json(proof_dir / "contradiction_packet_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", contradiction_review_packets + contradiction_cluster_packets)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
