"""Artifact writer for SQP-2 source quality scoring."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_quality_artifacts(
    *,
    proof_dir: Path,
    quality_scores: list[dict],
    feature_records: list[dict],
    policy: dict,
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "source_quality_scores.jsonl", quality_scores)
    write_jsonl(proof_dir / "source_quality_feature_records.jsonl", feature_records)
    write_json(proof_dir / "source_quality_policy.json", policy)
    write_json(proof_dir / "source_quality_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", feature_records + quality_scores)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
