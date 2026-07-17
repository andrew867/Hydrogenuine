"""Write P28-2 domain readiness artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p28_2_artifacts(proof_dir: Path, layer: dict) -> None:
    write_jsonl(proof_dir / "domain_pack_readiness_records.jsonl", layer["domain_pack_readiness_records"])
    write_jsonl(proof_dir / "domain_refusal_records.jsonl", layer["domain_refusal_records"])
    write_json(proof_dir / "domain_boundary_matrix.json", layer["boundary_matrix"])
    write_json(proof_dir / "domain_readiness_manifest.json", layer["readiness_manifest"])
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["replay_deterministic"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["domain_pack_readiness_records"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
