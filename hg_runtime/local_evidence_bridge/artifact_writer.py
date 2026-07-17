"""LEB proof artifact writer."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def write_leb0_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "operator_provided_sources.jsonl", layer["sources"])
    write_json(proof_dir / "local_source_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "local_evidence_receipts.jsonl", layer["evidence_receipts"])
    write_jsonl(proof_dir / "source_excerpt_receipts.jsonl", layer["excerpt_receipts"])
    write_json(proof_dir / "evidence_redaction_record.json", layer["redaction_record"])
    write_json(proof_dir / "evidence_boundary_receipt.json", layer["boundary_receipt"])
    write_json(proof_dir / "evidence_ingestion_request.json", layer["ingestion_request"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["no_secrets_in_receipts"]})


def write_leb1_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_json(proof_dir / "local_source_manifest.json", layer["source_manifest"])
    write_jsonl(proof_dir / "local_evidence_receipts.jsonl", layer["receipts"])
    write_jsonl(proof_dir / "source_excerpt_receipts.jsonl", layer["excerpts"])
    write_jsonl(proof_dir / "evidence_redaction_records.jsonl", layer["redactions"])
    write_json(proof_dir / "ingestion_manifest.json", layer["ingestion_manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["receipts"] + layer["excerpts"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})


def write_leb2_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "evidence_claim_links.jsonl", layer["links"])
    write_jsonl(proof_dir / "evidence_support_records.jsonl", layer["supports"])
    write_jsonl(proof_dir / "evidence_contradiction_records.jsonl", layer["contradictions"])
    write_jsonl(proof_dir / "wmbr_verification_task_links.jsonl", layer["task_links"])
    write_json(proof_dir / "wmbr_bridge_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["links"] + layer["supports"] + layer["contradictions"] + layer["task_links"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})


def write_leb3_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "local_evidence_belief_states.jsonl", layer["run"]["belief_states"])
    write_jsonl(proof_dir / "local_evidence_belief_revisions.jsonl", layer["run"]["belief_revisions"])
    write_jsonl(proof_dir / "local_evidence_contradictions.jsonl", layer["run"]["local_contradictions"])
    write_jsonl(proof_dir / "local_evidence_provenance_chains.jsonl", layer["run"]["provenance_chains"])
    write_json(proof_dir / "local_revision_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["run"]["belief_states"]
        + layer["run"]["belief_revisions"]
        + layer["run"]["local_contradictions"]
        + layer["run"]["provenance_chains"],
    )
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})
