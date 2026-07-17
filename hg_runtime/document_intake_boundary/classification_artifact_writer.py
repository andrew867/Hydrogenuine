"""Artifact writer for DIB-1 classification."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_classification_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "file_type_classifier_manifest.json", layer["file_type_classifier_manifest"])
    write_jsonl(proof_dir / "document_type_classifications.jsonl", layer["document_type_classifications"])
    write_jsonl(proof_dir / "document_file_records.jsonl", layer["document_file_records"])
    write_jsonl(proof_dir / "rejected_document_records.jsonl", layer["rejected_document_records"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["document_type_classifications"] + layer["document_file_records"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
