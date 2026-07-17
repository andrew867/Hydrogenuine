"""Deterministic P26-0 schema fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.experience_record import build_experience_record
from hg_runtime.experience_ledger.hashing import stable_hash, with_hash
from hg_runtime.experience_ledger.ledger_policy import build_experience_ledger_policy
from hg_runtime.experience_ledger.memory_record import build_memory_record
from hg_runtime.experience_ledger.promotion_request import (
    build_memory_promotion_decision,
    build_memory_promotion_request,
)
from hg_runtime.experience_ledger.recall_record import build_recall_query, build_recall_result
from hg_runtime.experience_ledger.schemas import PHASE19_VERDICT, PHASE24_STATUS, P26_INVARIANTS, assert_neutral


def build_memory_retraction_record(memory_record: dict) -> dict:
    record = {
        "record_type": "memory_retraction_record_v1",
        "schema_version": "1",
        "retraction_id": f"retract-{memory_record['memory_id']}",
        "memory_id": memory_record["memory_id"],
        "memory_hash": memory_record["memory_hash"],
        "retraction_is_erasure": False,
        "original_memory_preserved": True,
        "deletion_performed": False,
    }
    with_hash(record, "retraction_hash")
    assert_neutral(record)
    return record


def replay_p26_0(records: list[dict]) -> dict:
    hashes = [stable_hash(r) for r in records]
    return {
        "record_type": "operator_review_replay_record_v1",
        "schema_version": "1",
        "replay_preserves_record_hashes": all(bool(h) for h in hashes),
        "receipt_chain_root": stable_hash({"hashes": hashes}),
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
    }


def build_p26_0_layer(repo_root: Path) -> dict:
    policy = build_experience_ledger_policy()
    experience = build_experience_record(
        experience_id="exp-sle-rc",
        family="SLE-RC",
        artifact_ref="docs/proofs/autonomous_agent_zero/SLE-SAFE-LOCAL-EVIDENCE-RELEASE-CANDIDATE/20260620T220533Z",
        verdict="GREEN_SLE_SAFE_LOCAL_EVIDENCE_RELEASE_CANDIDATE",
        boundary_tags=["release_candidate_not_deployment", "evidence_not_truth", "phase19_yellow"],
        provenance_refs=["rc_artifact_index.json", "rc_boundary_matrix.json"],
    )
    memory = build_memory_record(
        memory_id="mem-sle-rc",
        experience_record=experience,
        provenance_refs=experience["provenance_refs"],
        source_quality_refs=["SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION"],
    )
    query = build_recall_query(query_id="query-family-sle-rc", query_type="by_family", value="SLE-RC")
    recall = build_recall_result(result_id="result-family-sle-rc", query=query, memory_records=[memory])
    request = build_memory_promotion_request(request_id="request-mem-sle-rc", memory_record=memory)
    decision = build_memory_promotion_decision(decision_id="decision-mem-sle-rc", request=request)
    retraction = build_memory_retraction_record(memory)
    records = [policy, experience, memory, query, recall, request, decision, retraction]
    manifest = {
        "record_type": "experience_ledger_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p26-0-schema-fixture",
        "repo_root": str(repo_root),
        "record_count": len(records),
        "invariants": P26_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
        "experience_treated_as_evidence_by_itself": False,
        "belief_promotion_automatic": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_external_side_effects_created": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {
        "policy": policy,
        "experience_records": [experience],
        "memory_records": [memory],
        "recall_queries": [query],
        "recall_results": [recall],
        "promotion_requests": [request],
        "promotion_decisions": [decision],
        "retraction_records": [retraction],
        "manifest": manifest,
        "replay": replay_p26_0(records),
        "records": records,
    }
