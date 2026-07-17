"""Artifact writer for SQP-1 duplicate detection."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl
from hg_runtime.source_quality_provenance.hashing import record_hash


def write_duplicate_artifacts(
    *,
    proof_dir: Path,
    identities: list[dict],
    fingerprints: list[dict],
    duplicate_records: list[dict],
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "source_identity_records.jsonl", identities)
    write_jsonl(proof_dir / "source_fingerprints.jsonl", fingerprints)
    write_jsonl(proof_dir / "duplicate_source_records.jsonl", duplicate_records)
    write_json(proof_dir / "duplicate_detection_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", identities + fingerprints + duplicate_records)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
    write_json(proof_dir / "artifact_manifest.json", {"artifact_hash": record_hash(manifest), "artifact_count": 7})
