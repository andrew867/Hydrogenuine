"""Artifact writer for DTX-4 soak."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_dtx_soak_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "dtx_soak_manifest.json", layer["dtx_soak_manifest"])
    write_jsonl(proof_dir / "dtx_soak_iterations.jsonl", layer["dtx_soak_iterations"])
    write_json(proof_dir / "dtx_stable_hashes.json", layer["dtx_stable_hashes"])
    write_jsonl(proof_dir / "dtx_mutation_probes.jsonl", layer["dtx_mutation_probes"])
    write_jsonl(proof_dir / "dtx_mutation_results.jsonl", layer["dtx_mutation_results"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["dtx_soak_iterations"] + layer["dtx_mutation_results"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
