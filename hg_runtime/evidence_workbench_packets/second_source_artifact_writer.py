"""Artifact writer for EWP-2 second-source gate."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_second_source_artifacts(
    *,
    proof_dir: Path,
    requirements: list[dict],
    results: list[dict],
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "packet_second_source_requirements.jsonl", requirements)
    write_jsonl(proof_dir / "packet_second_source_results.jsonl", results)
    write_json(proof_dir / "second_source_gate_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", requirements + results)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
