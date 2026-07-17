"""AEC-01 / CAGI-48 replay — deterministic re-derivation of experiment artifacts."""

from __future__ import annotations

from hg_runtime.active_experiment_harness.artifact_writer import (
    build_experiment_artifacts,
)
from hg_runtime.active_experiment_harness.fixtures import (
    fixture_experiment_hypotheses,
    fixture_experiment_plans,
    fixture_experiment_results,
)


def replay_experiment_artifacts() -> dict:
    hypotheses = fixture_experiment_hypotheses()
    plans = fixture_experiment_plans()
    outcomes = [
        [
            {"context_window": 2048, "accuracy": 0.72, "source": "fixture"},
            {"context_window": 4096, "accuracy": 0.78, "source": "fixture"},
            {"context_window": 8192, "accuracy": 0.81, "source": "fixture"},
        ],
        [],
    ]
    return build_experiment_artifacts(hypotheses, plans, outcomes)
