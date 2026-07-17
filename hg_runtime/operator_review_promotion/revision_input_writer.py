"""ORP-3 promotion gate manifest and artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl
from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_promotion_gate_manifest(*, request_manifest: dict, gate_results: list[dict], revision_inputs: list[dict]) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "promotion_gate_manifest_v1",
        "manifest_id": "orp3-promotion-gate-manifest",
        "source_promotion_request_manifest_hash": request_manifest["manifest_hash"],
        "promotion_gate_result_count": len(gate_results),
        "revision_input_count": len(revision_inputs),
        "promotion_gate_hashes": [r["gate_hash"] for r in gate_results],
        "revision_input_hashes": [r["record_hash"] for r in revision_inputs],
        "gate_pass_is_truth": False,
        "gate_pass_is_certainty": False,
        "gate_pass_is_action_permission": False,
        "gate_fail_is_deletion": False,
        "revision_input_is_belief_state": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "old_proof_mutated": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def write_orp3_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "promotion_gate_results.jsonl", layer["promotion_gate_results"])
    write_jsonl(proof_dir / "promotion_gated_revision_inputs.jsonl", layer["promotion_gated_revision_inputs"])
    write_json(proof_dir / "promotion_gate_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["promotion_gate_results"] + layer["promotion_gated_revision_inputs"],
    )
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})
