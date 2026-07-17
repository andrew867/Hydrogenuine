"""Artifact writer for DIB-4 PDF disabled gate."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_pdf_disabled_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "pdf_disabled_policy.json", layer["pdf_disabled_policy"])
    write_jsonl(proof_dir / "pdf_rejection_records.jsonl", layer["pdf_rejection_records"])
    write_json(proof_dir / "pdf_disabled_gate_manifest.json", layer["pdf_disabled_gate_manifest"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["pdf_rejection_records"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
