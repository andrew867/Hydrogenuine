"""Artifact writer for DTX-1 document corpus."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_dtx_corpus_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "dtx_manifest.json", layer["dtx_manifest"])
    write_jsonl(proof_dir / "dtx_document_fixtures.jsonl", layer["dtx_document_fixtures"])
    write_jsonl(proof_dir / "dtx_expected_outcomes.jsonl", layer["dtx_expected_outcomes"])
    write_json(proof_dir / "dtx_corpus_validation_result.json", layer["validation"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["dtx_document_fixtures"] + layer["dtx_expected_outcomes"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
