"""Write SLE-RC-3 soak artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_sle_rc3_artifacts(proof_dir: Path, layer: dict) -> None:
    write_jsonl(proof_dir / "rc_soak_iterations.jsonl", layer["rc_soak_iterations"])
    write_json(proof_dir / "rc_stable_hashes.json", layer["rc_stable_hashes"])
    write_json(proof_dir / "rc_replay_result.json", layer["rc_replay_result"])
    write_json(proof_dir / "rc_mutation_summary.json", layer["rc_mutation_summary"])
    write_json(proof_dir / "rc_soak_manifest.json", layer["rc_soak_manifest"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["rc_soak_iterations"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
