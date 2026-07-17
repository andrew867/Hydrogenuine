"""AEC-03 / CAGI-50 replay — deterministic re-derivation of transfer artifacts."""

from __future__ import annotations

from hg_runtime.novelty_transfer_evaluation.artifact_writer import build_transfer_artifacts
from hg_runtime.novelty_transfer_evaluation.fixtures import (
    fixture_baseline_scores,
    fixture_novelty_tasks,
    fixture_transfer_scores,
)


def replay_transfer_artifacts() -> dict:
    return build_transfer_artifacts(
        fixture_baseline_scores(),
        fixture_novelty_tasks(),
        fixture_transfer_scores(),
    )
