"""Artifact writer for DIB-2 parser sandbox."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_parser_sandbox_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "parser_sandbox_policy.json", layer["parser_sandbox_policy"])
    write_json(proof_dir / "parser_registry.json", layer["parser_registry"])
    write_json(proof_dir / "parser_sandbox_manifest.json", layer["parser_sandbox_manifest"])
    write_jsonl(proof_dir / "extraction_failure_records.jsonl", layer["parser_failure_records"])
    write_jsonl(proof_dir / "parser_quarantine_records.jsonl", layer["parser_quarantine_records"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["parser_evaluations"] + layer["parser_failure_records"] + layer["parser_quarantine_records"],
    )
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
