"""Artifact writer for DIB-3 safe text extraction."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_extraction_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "safe_text_extraction_manifest.json", layer["safe_text_extraction_manifest"])
    write_jsonl(proof_dir / "extraction_receipts.jsonl", layer["extraction_receipts"])
    write_jsonl(proof_dir / "extraction_failure_records.jsonl", layer["extraction_failure_records"])
    write_jsonl(proof_dir / "document_redaction_records.jsonl", layer["document_redaction_records"])
    write_jsonl(proof_dir / "document_source_identity_records.jsonl", layer["document_source_identity_records"])
    write_jsonl(proof_dir / "document_provenance_adapter_records.jsonl", layer["document_provenance_adapter_records"])
    write_jsonl(proof_dir / "dib_to_leb_adapter_records.jsonl", layer["dib_to_leb_adapter_records"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["extraction_receipts"]
        + layer["extraction_failure_records"]
        + layer["dib_to_leb_adapter_records"],
    )
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
