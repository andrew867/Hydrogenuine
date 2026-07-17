"""Artifact writer for the Phase 25 advisory self-improvement loop."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_advisory_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "advisory_improvement_proposals.jsonl", layer["proposals"])
    write_jsonl(proof_dir / "advisory_risk_records.jsonl", layer["risks"])
    write_jsonl(proof_dir / "advisory_operator_review_tasks.jsonl", layer["review_tasks"])
    write_jsonl(proof_dir / "advisory_refusal_records.jsonl", layer["refusals"])
    write_json(proof_dir / "phase25_manifest.json", layer["manifest"])
    write_json(proof_dir / "phase25_input_summary.json", layer["inputs"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["proposals"] + layer["risks"] + layer["review_tasks"] + layer["refusals"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
