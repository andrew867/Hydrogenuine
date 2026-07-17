"""DTX-4 document text exchange soak runner."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.dtx_pipeline import run_dtx_pipeline
from hg_runtime.document_text_exchange.dtx_soak import build_dtx_soak_iteration, build_dtx_soak_manifest
from hg_runtime.document_text_exchange.schemas import SOAK_ITERATION_COUNT, record_hash


def run_dtx_document_soak(root: Path, *, iteration_count: int = SOAK_ITERATION_COUNT) -> dict:
    baseline = run_dtx_pipeline(root)
    expected_hash = baseline["stable_hash"]
    iterations = []
    for i in range(1, iteration_count + 1):
        layer = run_dtx_pipeline(root)
        match = layer["stable_hash"] == expected_hash
        iterations.append(
            build_dtx_soak_iteration(
                iteration_id=f"dtx-iter-{i:03d}",
                iteration_number=i,
                stable_hash=layer["stable_hash"],
                replay_match=match,
            )
        )
    stable_hashes = [row["stable_hash"] for row in iterations]
    manifest = build_dtx_soak_manifest(
        manifest_id="dtx-soak-manifest-v1",
        dtx_manifest_ref=baseline["dtx_manifest_ref"],
        iteration_count=iteration_count,
    )
    return {
        "dtx_soak_manifest": manifest,
        "dtx_soak_iterations": iterations,
        "dtx_stable_hashes": {
            "expected_hash": expected_hash,
            "iteration_hashes": stable_hashes,
            "stable_hash_record_hash": record_hash({"hashes": stable_hashes}),
        },
        "soak_replay_result": {
            "iteration_count": iteration_count,
            "all_iterations_match": all(row["replay_match"] for row in iterations),
            "replay_deterministic": all(row["replay_match"] for row in iterations),
        },
        "baseline_layer": baseline,
    }


def run_dtx_document_soak_with_mutations(root: Path, *, iteration_count: int = SOAK_ITERATION_COUNT) -> dict:
    from hg_runtime.document_text_exchange.dtx_mutation_probe import build_mutation_layer

    soak = run_dtx_document_soak(root, iteration_count=iteration_count)
    mutation = build_mutation_layer(soak["baseline_layer"])
    return {**soak, **mutation}
