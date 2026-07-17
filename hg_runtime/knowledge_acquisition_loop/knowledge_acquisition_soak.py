"""P30-3 knowledge acquisition soak — stability and mutation detection."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.knowledge_acquisition_loop.acquisition_loop import build_acquisition_loop_layer
from hg_runtime.knowledge_acquisition_loop.hashing import stable_hash
from hg_runtime.knowledge_acquisition_loop.schemas import SOAK_ITERATION_COUNT


def stable_run_material(layer: dict) -> dict:
    manifest_hash = layer["manifest"]["manifest_hash"]
    result_hashes = [r.get("result_hash", "") for r in layer["results"]]
    refusal_hashes = [r.get("refusal_hash", "") for r in layer["refusals"]]
    return {
        "manifest_hash": manifest_hash,
        "result_hashes": result_hashes,
        "refusal_hashes": refusal_hashes,
    }


def run_knowledge_acquisition_soak(repo_root: Path) -> dict:
    baseline_layer = build_acquisition_loop_layer(repo_root)
    baseline = stable_run_material(baseline_layer)
    baseline_composite = stable_hash(baseline)

    iterations = []
    all_match = True

    for i in range(SOAK_ITERATION_COUNT):
        layer = build_acquisition_loop_layer(repo_root)
        material = stable_run_material(layer)
        composite = stable_hash(material)
        match = composite == baseline_composite
        if not match:
            all_match = False
        iterations.append({
            "iteration": i + 1,
            "composite_hash": composite,
            "matches_baseline": match,
        })

    return {
        "baseline_composite": baseline_composite,
        "iteration_count": SOAK_ITERATION_COUNT,
        "iterations": iterations,
        "all_stable": all_match,
        "baseline_layer": baseline_layer,
    }
