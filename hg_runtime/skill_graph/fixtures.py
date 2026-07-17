"""Deterministic P27-0 schema fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.hashing import stable_hash, with_hash
from hg_runtime.skill_graph.p27_schemas import PHASE19_VERDICT, PHASE24_STATUS, P27_INVARIANTS, assert_neutral
from hg_runtime.skill_graph.skill_edge import build_skill_edge
from hg_runtime.skill_graph.skill_policy import build_skill_graph_policy
from hg_runtime.skill_graph.skill_record import build_skill_record
from hg_runtime.skill_graph.transfer_record import (
    build_skill_source_memory_link,
    build_transfer_candidate,
    build_transfer_result,
)


def build_p27_0_layer(repo_root: Path) -> dict:
    policy = build_skill_graph_policy()
    skill = build_skill_record(
        skill_id="skill-fixture-001",
        skill_name="bounded_release_review",
        procedure_tag="review_release_candidate",
        domain_hint="SLE-RC",
        boundary_tags=["release_candidate_not_deployment", "evidence_not_truth"],
        memory_id="mem-artifact-sle-rc",
        memory_hash="sha256:fixture-memory-hash",
        provenance_refs=["rc_artifact_index.json", "rc_boundary_matrix.json"],
        source_quality_refs=["SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION"],
        confidence_descriptive=0.42,
    )
    skill_b = build_skill_record(
        skill_id="skill-fixture-002",
        skill_name="advisory_self_improvement_review",
        procedure_tag="review_advisory_proposal",
        domain_hint="PHASE-25",
        boundary_tags=["advisory_not_patch_permission", "operator_review_required"],
        memory_id="mem-artifact-phase25",
        memory_hash="sha256:fixture-memory-hash-002",
        provenance_refs=["proposal_records.jsonl"],
        confidence_descriptive=0.35,
    )
    edge = build_skill_edge(
        edge_id="edge-fixture-001",
        source_skill_id=skill["skill_id"],
        target_skill_id=skill_b["skill_id"],
        edge_type="shared_boundary_tag_review",
        evidence_refs=["release_candidate_not_deployment"],
    )
    link = build_skill_source_memory_link(
        link_id="link-fixture-001",
        skill_id=skill["skill_id"],
        memory_id=skill["memory_id"],
        memory_hash=skill["memory_hash"],
    )
    candidate = build_transfer_candidate(
        candidate_id="transfer-fixture-001",
        source_skill_id=skill["skill_id"],
        target_skill_id=skill_b["skill_id"],
        source_domain="SLE-RC",
        target_domain="PHASE-25",
        link_reason="shared_review_procedure_shape",
        evidence_refs=skill["provenance_refs"],
        provenance_refs=skill["provenance_refs"],
    )
    transfer_result = build_transfer_result(
        result_id="transfer-result-fixture-001",
        candidate_id=candidate["candidate_id"],
        outcome="hypothesis_recorded",
    )
    records = [policy, skill, skill_b, edge, link, candidate, transfer_result]
    manifest = {
        "record_type": "skill_graph_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p27-0-schema-fixture",
        "repo_root": str(repo_root),
        "record_count": len(records),
        "invariants": P27_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "explicit_manifest_only": True,
        "skill_treated_as_authority": False,
        "transfer_treated_as_proof": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    replay = {
        "record_type": "skill_graph_replay_v1",
        "schema_version": "1",
        "replay_preserves_record_hashes": True,
        "receipt_chain_root": stable_hash({"hashes": [stable_hash(r) for r in records]}),
    }
    return {
        "policy": policy,
        "skill_records": [skill, skill_b],
        "skill_edges": [edge],
        "skill_source_memory_links": [link],
        "transfer_candidates": [candidate],
        "transfer_results": [transfer_result],
        "manifest": manifest,
        "replay": replay,
        "records": records,
    }
