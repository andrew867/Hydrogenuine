"""ORP decision ledger proof artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_orp1_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "operator_review_decisions.jsonl", layer["decisions"])
    write_json(proof_dir / "operator_review_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "reviewed_evidence_links.jsonl", layer["reviewed_evidence_links"])
    write_jsonl(proof_dir / "operator_rejection_records.jsonl", layer["operator_rejection_records"])
    write_jsonl(proof_dir / "operator_deferral_records.jsonl", layer["operator_deferral_records"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["decisions"]
        + layer["reviewed_evidence_links"]
        + layer["operator_rejection_records"]
        + layer["operator_deferral_records"],
    )
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})
