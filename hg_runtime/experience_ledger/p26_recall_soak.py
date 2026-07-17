"""P26-4 deterministic recall and promotion replay soak."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.hashing import stable_hash, with_hash
from hg_runtime.experience_ledger.promotion_decision_ledger import build_p26_3_bridge
from hg_runtime.experience_ledger.recall_index import build_recall_index
from hg_runtime.experience_ledger.recall_query import make_query
from hg_runtime.experience_ledger.recall_surface import build_recall_surface_run
from hg_runtime.experience_ledger.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral


def default_soak_queries() -> list[dict]:
    return [
        make_query("by_family", "SLE-RC"),
        make_query("by_verdict", "GREEN_PHASE25_ADVISORY_SELF_IMPROVEMENT"),
        make_query("by_boundary_tag", "p26_not_complete"),
        make_query("by_time_window", "ALL_FIXTURE_TIME"),
    ]


def stable_run_material(repo_root: Path) -> dict:
    recall_index = build_recall_index(repo_root)
    recall_run = build_recall_surface_run(default_soak_queries(), recall_index)
    promotion = build_p26_3_bridge(repo_root)
    return {
        "recall_index_hash": recall_index["index"]["manifest_hash"],
        "recall_manifest_hash": recall_run["manifest"]["manifest_hash"],
        "recall_result_hashes": [result["recall_hash"] for result in recall_run["results"]],
        "promotion_manifest_hash": promotion["manifest"]["manifest_hash"],
        "promotion_decision_hashes": [decision["decision_hash"] for decision in promotion["decisions"]],
    }


def run_recall_soak(repo_root: Path, iterations: int = 5) -> dict:
    records = []
    stable_roots = []
    for index in range(iterations):
        material = stable_run_material(repo_root)
        stable_root = stable_hash(material)
        record = {
            "record_type": "p26_recall_soak_iteration_v1",
            "schema_version": "1",
            "iteration": index + 1,
            "stable_root": stable_root,
            "timestamp_proof_path_noise_excluded": True,
            "memory_treated_as_truth": False,
            "recall_treated_as_authority": False,
            "promotion_request_is_promotion": False,
            "belief_promoted": False,
            "orp_bypassed": False,
        }
        with_hash(record, "record_hash")
        assert_neutral(record)
        records.append(record)
        stable_roots.append(stable_root)
    manifest = {
        "record_type": "p26_recall_soak_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p26-4-recall-replay-soak",
        "iteration_count": iterations,
        "stable_root": stable_roots[0],
        "all_iterations_match": len(set(stable_roots)) == 1,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "mutation_auto_repair_performed": False,
        "original_artifacts_mutated": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_external_side_effects_created": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    stable_hashes = {
        "record_type": "p26_stable_hashes_v1",
        "schema_version": "1",
        "stable_roots": stable_roots,
        "all_iterations_match": len(set(stable_roots)) == 1,
        "timestamp_proof_path_noise_excluded": True,
    }
    return {"iterations": records, "stable_hashes": stable_hashes, "manifest": manifest}
