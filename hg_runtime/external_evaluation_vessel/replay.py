"""LHRE-03 / CAGI-56 replay."""

from __future__ import annotations

from hg_runtime.external_evaluation_vessel.artifact_writer import build_vessel_artifacts
from hg_runtime.external_evaluation_vessel.fixtures import (
    fixture_evaluation_vessels,
    fixture_evaluator_provenance,
    fixture_task_bundles,
    fixture_vessel_results,
)


def replay_vessel_artifacts() -> dict:
    return build_vessel_artifacts(
        fixture_evaluation_vessels(),
        fixture_task_bundles(),
        fixture_evaluator_provenance(),
        fixture_vessel_results(),
    )
