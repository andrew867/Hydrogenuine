"""Write SLE-RC-1 component status artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl
from hg_runtime.safe_local_evidence_rc.schemas import record_hash


def write_sle_rc1_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "rc_artifact_index.json", layer["rc_artifact_index"])
    write_jsonl(proof_dir / "rc_component_statuses.jsonl", layer["rc_component_statuses"])
    write_json(proof_dir / "rc_proof_bundle_index.json", layer["proof_bundle_index"])
    write_json(proof_dir / "rc_report_index.json", layer["report_index"])
    write_jsonl(proof_dir / "rc_gate_statuses.jsonl", layer["gate_statuses"])
    manifest = {
        "schema_version": "1",
        "artifact_count": 6,
        "all_consolidations_green": layer["all_consolidations_green"],
        "manifest_hash": record_hash(layer["rc_artifact_index"]),
    }
    write_json(proof_dir / "rc_artifact_index_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["replay_deterministic"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["rc_component_statuses"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
