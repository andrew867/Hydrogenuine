"""P31 evaluation replay — deterministic replay of fixture runs."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.fixture_runner import run_fixtures
from hg_runtime.evaluation_harness.hashing import stable_hash


def replay_evaluation(
    fixtures: list[dict[str, Any]],
    observed_outputs: dict[str, dict[str, Any]],
    model_id: str,
    iterations: int = 1,
) -> dict[str, Any]:
    hashes = []
    summaries = []

    for i in range(iterations):
        summary = run_fixtures(fixtures, observed_outputs, model_id)
        run_hash = stable_hash({
            "passed": summary["passed"],
            "failed": summary["failed"],
            "deferred": summary["deferred"],
            "coverage": summary["coverage"],
        })
        hashes.append(run_hash)
        summaries.append({
            "iteration": i,
            "passed": summary["passed"],
            "failed": summary["failed"],
            "deferred": summary["deferred"],
            "hash": run_hash,
        })

    unique_hashes = set(hashes)
    return {
        "iterations": iterations,
        "hashes": hashes,
        "unique_hashes": len(unique_hashes),
        "deterministic": len(unique_hashes) == 1,
        "summaries": summaries,
        "replay_is_not_truth": True,
    }
