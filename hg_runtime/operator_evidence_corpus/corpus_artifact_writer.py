"""Artifact writer for OEC-1 curated corpus."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_corpus_artifacts(
    *,
    proof_dir: Path,
    records: dict,
    validation_result: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "corpus_manifest.json", records["corpus_manifest"])
    write_jsonl(proof_dir / "corpus_sources.jsonl", records["corpus_sources"])
    write_jsonl(proof_dir / "corpus_claims.jsonl", records["corpus_claims"])
    write_jsonl(proof_dir / "corpus_expected_outcomes.jsonl", records["corpus_expected_outcomes"])
    write_json(proof_dir / "corpus_validation_result.json", validation_result)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        records["corpus_sources"]
        + records["corpus_claims"]
        + records["corpus_expected_outcomes"]
        + records["corpus_claim_packets"],
    )
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
