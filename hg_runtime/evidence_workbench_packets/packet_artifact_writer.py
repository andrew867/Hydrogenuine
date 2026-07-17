"""Artifact writer for EWP-1 claim evidence packets."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_packet_artifacts(
    *,
    proof_dir: Path,
    claim_evidence_packets: list[dict],
    packet_source_summaries: list[dict],
    packet_support_records: list[dict],
    packet_contradiction_records: list[dict],
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "claim_evidence_packets.jsonl", claim_evidence_packets)
    write_jsonl(proof_dir / "packet_source_summaries.jsonl", packet_source_summaries)
    write_jsonl(proof_dir / "packet_support_records.jsonl", packet_support_records)
    write_jsonl(proof_dir / "packet_contradiction_records.jsonl", packet_contradiction_records)
    write_json(proof_dir / "packet_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        claim_evidence_packets
        + packet_source_summaries
        + packet_support_records
        + packet_contradiction_records,
    )
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
