"""ORP-4 reviewed local belief revision manifest and artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl
from hg_runtime.operator_review_promotion.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_reviewed_revision_manifest(run: dict) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "reviewed_revision_manifest_v1",
        "manifest_id": "orp4-promotion-gated-belief-revision",
        "reviewed_belief_state_count": len(run["reviewed_belief_states"]),
        "reviewed_belief_revision_count": len(run["reviewed_belief_revisions"]),
        "reviewed_contradiction_count": len(run["reviewed_local_contradictions"]),
        "reviewed_provenance_chain_count": len(run["reviewed_local_provenance_chains"]),
        "reviewed_belief_state_hashes": [r["record_hash"] for r in run["reviewed_belief_states"]],
        "reviewed_belief_revision_hashes": [r["record_hash"] for r in run["reviewed_belief_revisions"]],
        "reviewed_contradiction_hashes": [r["record_hash"] for r in run["reviewed_local_contradictions"]],
        "reviewed_provenance_chain_hashes": [r["record_hash"] for r in run["reviewed_local_provenance_chains"]],
        "reviewed_belief_is_still_provisional": True,
        "operator_reviewed_means_true": False,
        "support_remains_provisionally_supported": True,
        "rejected_evidence_excluded_but_preserved": True,
        "old_records_preserved": True,
        "old_wmbr_proof_bundles_mutated": False,
        "old_leb_proof_bundles_mutated": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def write_orp4_artifacts(layer: dict, summary: dict, proof_dir: Path) -> None:
    run = layer["run"]
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "reviewed_local_belief_states.jsonl", run["reviewed_belief_states"])
    write_jsonl(proof_dir / "reviewed_local_belief_revisions.jsonl", run["reviewed_belief_revisions"])
    write_jsonl(proof_dir / "reviewed_local_contradictions.jsonl", run["reviewed_local_contradictions"])
    write_jsonl(proof_dir / "reviewed_local_provenance_chains.jsonl", run["reviewed_local_provenance_chains"])
    write_json(proof_dir / "reviewed_revision_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        run["reviewed_belief_states"]
        + run["reviewed_belief_revisions"]
        + run["reviewed_local_contradictions"]
        + run["reviewed_local_provenance_chains"],
    )
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})
