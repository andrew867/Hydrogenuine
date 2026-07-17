"""OES-1 repeated corpus replay iteration runner."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_soak.corpus_replay_soak import run_corpus_pipeline
from hg_runtime.operator_evidence_soak.schemas import SOAK_ITERATION_COUNT
from hg_runtime.operator_evidence_soak.soak_iteration import build_soak_iteration_result, build_soak_replay_result
from hg_runtime.operator_evidence_soak.soak_policy import build_operator_evidence_soak, build_soak_manifest, build_soak_policy
from hg_runtime.operator_evidence_soak.boundary_assertions import build_default_boundary_assertions
from hg_runtime.operator_evidence_soak.stable_hash import stable_hash


def run_repeated_corpus_soak(root: Path, *, iteration_count: int = SOAK_ITERATION_COUNT) -> dict:
    baseline = run_corpus_pipeline(root)
    expected_hash = baseline["stable_hash"]
    iterations = []
    for i in range(1, iteration_count + 1):
        layer = run_corpus_pipeline(root)
        match = layer["stable_hash"] == expected_hash
        iterations.append(
            build_soak_iteration_result(
                iteration_id=f"oes-iter-{i:03d}",
                iteration_number=i,
                stable_hash=layer["stable_hash"],
                replay_match=match,
            )
        )
    stable_hashes = [row["stable_hash"] for row in iterations]
    all_match = all(row["replay_match"] for row in iterations)
    policy = build_soak_policy(iteration_count=iteration_count)
    soak = build_operator_evidence_soak(soak_id="oes-corpus-replay-soak-v1", manifest_id="oes-corpus-replay-manifest-v1")
    manifest = build_soak_manifest(
        manifest_id="oes-corpus-replay-manifest-v1",
        corpus_manifest_ref=baseline["corpus_manifest_ref"],
        iteration_count=iteration_count,
    )
    replay = build_soak_replay_result(iteration_count=iteration_count, stable_hashes=stable_hashes, all_match=all_match)
    return {
        "operator_evidence_soak": soak,
        "soak_policy": policy,
        "soak_manifest": manifest,
        "soak_iterations": iterations,
        "soak_replay_result": replay,
        "stable_hashes": {"expected_hash": expected_hash, "iteration_hashes": stable_hashes, "stable_hash_record_hash": stable_hash({"hashes": stable_hashes})},
        "boundary_assertions": build_default_boundary_assertions(),
        "baseline_layer": baseline,
    }
