"""LHRE-04 / CAGI-57 replay."""

from __future__ import annotations

from hg_runtime.heldout_external_evaluation.artifact_writer import build_heldout_artifacts
from hg_runtime.heldout_external_evaluation.fixtures import (
    fixture_evaluation_attempts,
    fixture_heldout_tasks,
    fixture_leakage_checks,
)


def replay_heldout_artifacts() -> dict:
    return build_heldout_artifacts(
        fixture_heldout_tasks(),
        fixture_evaluation_attempts(),
        fixture_leakage_checks(),
    )
