"""P30-2 fixture-only acquisition loop — orchestrates simulation."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.knowledge_acquisition_loop.acquisition_loop_simulator import simulate_acquisition_loop
from hg_runtime.knowledge_acquisition_loop.acquisition_task_builder import build_acquisition_task_layer
from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P30_INVARIANTS,
    assert_neutral,
)


def build_acquisition_loop_layer(repo_root: Path) -> dict:
    task_layer = build_acquisition_task_layer(repo_root)

    sim = simulate_acquisition_loop(task_layer["tasks"], task_layer["sources"])

    manifest = {
        "record_type": "knowledge_acquisition_loop_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p30-2-acquisition-loop-fixture",
        "repo_root": str(repo_root),
        "task_count": len(task_layer["tasks"]),
        "result_count": len(sim["results"]),
        "refusal_count": len(sim["refusals"]),
        "operator_review_count": len(sim["operator_reviews"]),
        "unsourced_normalized_count": len(sim["unsourced_normalized"]),
        "covered_refusal_reasons": sim["covered_refusal_reasons"],
        "all_refusal_reasons_covered": sim["all_refusal_reasons_covered"],
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
        "task_layer": task_layer,
        "results": sim["results"],
        "refusals": sim["refusals"],
        "operator_reviews": sim["operator_reviews"],
        "unsourced_normalized": sim["unsourced_normalized"],
        "manifest": manifest,
    }


def replay_acquisition_loop(repo_root: Path, expected_manifest_hash: str) -> dict:
    layer = build_acquisition_loop_layer(repo_root)
    return {
        "replay_preserves_manifest_hash": layer["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replayed_manifest_hash": layer["manifest"]["manifest_hash"],
        "expected_manifest_hash": expected_manifest_hash,
    }
