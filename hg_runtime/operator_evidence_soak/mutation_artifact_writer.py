"""Artifact writer for OES-2 mutation replay."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_mutation_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "mutation_replay_manifest.json", layer["mutation_replay_manifest"])
    write_jsonl(proof_dir / "mutation_probes.jsonl", layer["mutation_probes"])
    write_jsonl(proof_dir / "mutation_results.jsonl", layer["mutation_results"])
    write_jsonl(proof_dir / "mismatch_records.jsonl", layer["mismatch_records"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_json(proof_dir / "boundary_assertions.json", {"assertions": layer["boundary_assertions"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["receipt_chain"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
