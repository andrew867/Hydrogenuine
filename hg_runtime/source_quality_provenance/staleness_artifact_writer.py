"""Artifact writer for SQP-4 staleness and conflict detection."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_staleness_conflict_artifacts(
    *,
    proof_dir: Path,
    staleness_records: list[dict],
    conflict_records: list[dict],
    conflict_clusters: list[dict],
    manifest: dict,
    policy: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "source_staleness_records.jsonl", staleness_records)
    write_jsonl(proof_dir / "source_conflict_records.jsonl", conflict_records)
    write_jsonl(proof_dir / "conflict_clusters.jsonl", conflict_clusters)
    write_json(proof_dir / "staleness_conflict_manifest.json", manifest)
    write_json(proof_dir / "staleness_conflict_policy.json", policy)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", staleness_records + conflict_records + conflict_clusters)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
