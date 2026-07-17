"""Write SLE-RC-2 boundary matrix artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_sle_rc2_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "rc_boundary_matrix.json", layer["rc_boundary_matrix"])
    write_jsonl(proof_dir / "rc_boundary_assertions.jsonl", layer["rc_boundary_assertions"])
    write_jsonl(proof_dir / "rc_boundary_failures.jsonl", layer["rc_boundary_failures"])
    write_json(proof_dir / "rc_boundary_matrix_manifest.json", layer["rc_boundary_matrix_manifest"])
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["replay_deterministic"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["rc_boundary_assertions"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
