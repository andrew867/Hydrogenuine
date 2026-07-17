"""P28-3 domain pack soak runner."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_readiness_gate import evaluate_domain_readiness_gate
from hg_runtime.domain_pack_runtime.hashing import stable_hash, with_hash
from hg_runtime.domain_pack_runtime.schemas import SOAK_ITERATION_COUNT, assert_neutral


def stable_run_material(repo_root: Path) -> dict:
    layer = evaluate_domain_readiness_gate(repo_root)
    return {
        "builder_manifest_hash": layer["builder_manifest"]["manifest_hash"],
        "pack_hashes": [row["pack_hash"] for row in layer["domain_packs"]],
        "readiness_manifest_hash": layer["readiness_manifest"]["manifest_hash"],
        "readiness_hashes": [row["readiness_hash"] for row in layer["domain_pack_readiness_records"]],
    }


def run_domain_pack_soak(repo_root: Path, *, iterations: int = SOAK_ITERATION_COUNT) -> dict:
    stable_roots = []
    iteration_records = []
    baseline = stable_hash(stable_run_material(repo_root))
    for i in range(1, iterations + 1):
        root = stable_hash(stable_run_material(repo_root))
        match = root == baseline
        record = {
            "record_type": "domain_pack_soak_iteration_v1",
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
        "record_type": "domain_pack_soak_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p28-3-domain-pack-soak",
        "iteration_count": iterations,
        "stable_root": baseline,
        "all_iterations_match": len(set(stable_roots)) == 1,
        "mutation_auto_repaired": False,
        "original_artifacts_mutated": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    stable_hashes = {
        "record_type": "domain_pack_stable_hashes_v1",
        "schema_version": "1",
        "stable_roots": stable_roots,
        "all_iterations_match": len(set(stable_roots)) == 1,
    }
    return {
        "iterations": iteration_records,
        "stable_hashes": stable_hashes,
        "manifest": manifest,
        "baseline_hash": baseline,
        "all_iterations_match": len(set(stable_roots)) == 1,
    }
