"""P27-3 skill graph soak runner."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.hashing import stable_hash, with_hash
from hg_runtime.skill_graph.p27_schemas import SOAK_ITERATION_COUNT, assert_neutral
from hg_runtime.skill_graph.transfer_candidate_builder import build_transfer_candidates


def stable_run_material(repo_root: Path) -> dict:
    layer = build_transfer_candidates(repo_root)
    return {
        "skill_graph_index_hash": layer["skill_graph_index"]["manifest_hash"],
        "skill_hashes": [row["skill_hash"] for row in layer["skill_records"]],
        "edge_hashes": [row["edge_hash"] for row in layer["skill_edges"]],
        "transfer_hashes": [row["transfer_hash"] for row in layer["transfer_candidates"]],
        "transfer_manifest_hash": layer["transfer_candidate_manifest"]["manifest_hash"],
    }


def run_skill_graph_soak(repo_root: Path, *, iterations: int = SOAK_ITERATION_COUNT) -> dict:
    stable_roots = []
    iteration_records = []
    baseline = stable_hash(stable_run_material(repo_root))
    for i in range(1, iterations + 1):
        root = stable_hash(stable_run_material(repo_root))
        match = root == baseline
        record = {
            "record_type": "skill_graph_soak_iteration_v1",
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
        "record_type": "skill_graph_soak_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p27-3-skill-graph-soak",
        "iteration_count": iterations,
        "stable_root": baseline,
        "all_iterations_match": len(set(stable_roots)) == 1,
        "mutation_auto_repaired": False,
        "original_artifacts_mutated": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    stable_hashes = {
        "record_type": "skill_graph_stable_hashes_v1",
        "schema_version": "1",
        "stable_roots": stable_roots,
        "all_iterations_match": len(set(stable_roots)) == 1,
    }
    return {
        "iterations": iteration_records,
        "stable_hashes": stable_hashes,
        "manifest": manifest,
        "baseline_hash": baseline,
    }
