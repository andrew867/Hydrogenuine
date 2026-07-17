"""Deterministic P30-0 schema fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.knowledge_acquisition_loop.acquisition_candidate import build_acquisition_candidate
from hg_runtime.knowledge_acquisition_loop.acquisition_result import build_acquisition_result
from hg_runtime.knowledge_acquisition_loop.acquisition_source import build_acquisition_source_record
from hg_runtime.knowledge_acquisition_loop.acquisition_task import build_acquisition_task
from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.knowledge_policy import build_knowledge_acquisition_policy
from hg_runtime.knowledge_acquisition_loop.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P30_INVARIANTS,
    assert_neutral,
)


def build_p30_0_layer(repo_root: Path) -> dict:
    policy = build_knowledge_acquisition_policy()

    candidate = build_acquisition_candidate(
        candidate_id="cand-fixture-001",
        description="SLE-RC gate result artifact",
        source_type="local_proof",
        provenance_refs=["rc_artifact_index.json"],
    )

    source = build_acquisition_source_record(
        source_id="src-fixture-001",
        source_type="local_proof",
        artifact_path="docs/proofs/autonomous_agent_zero/SLE-SAFE-LOCAL-EVIDENCE-RELEASE-CANDIDATE",
        provenance_refs=["rc_artifact_index.json"],
        quality_score="verified_local",
    )

    task = build_acquisition_task(
        task_id="task-fixture-001",
        task_type="read_local_proof",
        candidate_id=candidate["candidate_id"],
        description="Read SLE-RC proof bundle",
        source_refs=[source["source_id"]],
    )

    result = build_acquisition_result(
        result_id="result-fixture-001",
        task_id=task["task_id"],
        result_state="ACQUIRED_FIXTURE",
        source_id=source["source_id"],
        acquired_content="fixture_gate_result_content",
    )

    records = [policy, candidate, source, task, result]
    manifest = {
        "record_type": "knowledge_acquisition_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p30-0-schema-fixture",
        "repo_root": str(repo_root),
        "record_count": len(records),
        "invariants": P30_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "acquired_claim_treated_as_truth": False,
        "acquisition_result_treated_as_belief": False,
        "belief_promotion_automatic": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)

    return {
        "policy": policy,
        "candidates": [candidate],
        "sources": [source],
        "tasks": [task],
        "results": [result],
        "manifest": manifest,
    }


def replay_p30_0(repo_root: Path, expected_manifest_hash: str) -> dict:
    layer = build_p30_0_layer(repo_root)
    return {
        "replay_preserves_manifest_hash": layer["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replayed_manifest_hash": layer["manifest"]["manifest_hash"],
        "expected_manifest_hash": expected_manifest_hash,
    }
