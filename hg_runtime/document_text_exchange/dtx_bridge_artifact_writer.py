"""Artifact writer for DTX-2 DIB bridge."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_dtx_bridge_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "dtx_bridge_manifest.json", layer["dtx_bridge_manifest"])
    write_jsonl(proof_dir / "dtx_extraction_receipts.jsonl", layer["dtx_extraction_receipts"])
    write_jsonl(proof_dir / "dtx_extraction_failures.jsonl", layer["dtx_extraction_failures"])
    write_jsonl(proof_dir / "dtx_document_source_identities.jsonl", layer["dtx_document_source_identities"])
    write_jsonl(proof_dir / "dtx_document_provenance_adapter_records.jsonl", layer["dtx_document_provenance_adapter_records"])
    write_jsonl(proof_dir / "dtx_dib_to_leb_adapter_records.jsonl", layer["dtx_dib_to_leb_adapter_records"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["dtx_extraction_receipts"] + layer["dtx_leb_bridge_records"] + layer["dtx_extraction_failures"],
    )
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
