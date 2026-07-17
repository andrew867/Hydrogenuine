"""Artifact writer for P26 experience-ledger gap reconciliation."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p26_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "p26_acceptance_criteria_map.json", {"criteria": layer["acceptance_criteria"]})
    write_json(proof_dir / "p26_existing_artifact_map.json", {"entries": layer["existing_artifact_map"]})
    write_jsonl(proof_dir / "p26_gap_records.jsonl", layer["gap_records"])
    write_jsonl(proof_dir / "p26_recommendation_records.jsonl", layer["recommendation_records"])
    write_json(proof_dir / "p26_reconciliation_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["gap_records"] + layer["recommendation_records"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
