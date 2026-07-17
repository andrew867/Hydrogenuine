"""Write SLE-RC-X extended soak artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_extended_soak_artifacts(proof_dir: Path, layer: dict, *, secret_redaction_passed: bool) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "rc_extended_soak_manifest.json", layer["rc_extended_soak_manifest"])
    write_jsonl(proof_dir / "rc_extended_soak_iterations.jsonl", layer["rc_extended_soak_iterations"])
    write_json(proof_dir / "rc_extended_stable_hashes.json", layer["rc_extended_stable_hashes"])
    write_json(proof_dir / "rc_churn_analysis.json", layer["rc_churn_analysis"])
    write_jsonl(proof_dir / "rc_boundary_matrix_replays.jsonl", layer["rc_boundary_matrix_replays"])
    write_json(proof_dir / "rc_extended_replay_result.json", layer["rc_extended_replay_result"])
    write_json(proof_dir / "rc_regression_matrix.json", layer["rc_regression_matrix"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["rc_extended_soak_iterations"] + layer["rc_boundary_matrix_replays"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": secret_redaction_passed})
