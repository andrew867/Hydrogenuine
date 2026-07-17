"""P29-3 tool workbench soak runner."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.tool_mediated_workbench.hashing import stable_hash, with_hash
from hg_runtime.tool_mediated_workbench.schemas import SOAK_ITERATION_COUNT, assert_neutral
from hg_runtime.tool_mediated_workbench.workbench_dry_run import build_dry_run_layer


def stable_run_material(repo_root: Path) -> dict:
    layer = build_dry_run_layer(repo_root)
    return {
        "manifest_hash": layer["manifest"]["manifest_hash"],
        "plan_hashes": [p["plan_hash"] for p in layer["plan_layer"]["plans"]],
        "sandbox_hashes": [s["sandbox_hash"] for s in layer["sandbox_results"]],
        "refusal_hashes": [r["refusal_hash"] for r in layer["refusals"]],
        "receipt_hashes": [r["receipt_hash"] for r in layer["receipts"]],
    }


def run_tool_workbench_soak(repo_root: Path, *, iterations: int = SOAK_ITERATION_COUNT) -> dict:
    stable_roots = []
    iteration_records = []
    baseline = stable_hash(stable_run_material(repo_root))
    for i in range(1, iterations + 1):
        root = stable_hash(stable_run_material(repo_root))
        match = root == baseline
        record = {
            "record_type": "tool_workbench_soak_iteration_v1",
            "schema_version": "1",
            "iteration": i,
            "stable_root": root,
            "replay_match": match,
            "timestamp_proof_path_noise_excluded": True,
            "soak_is_not_proof": True,
            "replay_match_is_not_truth": True,
            "mutation_auto_repaired": False,
        }
        with_hash(record, "record_hash")
        assert_neutral(record)
        iteration_records.append(record)
        stable_roots.append(root)
    manifest = {
        "record_type": "tool_workbench_soak_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p29-3-tool-workbench-soak",
        "iteration_count": iterations,
        "stable_root": baseline,
        "all_iterations_match": len(set(stable_roots)) == 1,
        "mutation_auto_repaired": False,
        "original_artifacts_mutated": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {
        "iterations": iteration_records,
        "stable_hashes": {
            "stable_roots": stable_roots,
            "all_iterations_match": len(set(stable_roots)) == 1,
        },
        "manifest": manifest,
        "baseline_hash": baseline,
        "all_iterations_match": len(set(stable_roots)) == 1,
    }
