"""SIEW-01 / CAGI-63 replay."""

from __future__ import annotations

from hg_runtime.economic_work_simulation.artifact_writer import build_simulation_artifacts
from hg_runtime.economic_work_simulation.fixtures import (
    fixture_simulated_tasks,
    fixture_work_artifacts,
)


def replay_simulation_artifacts() -> dict:
    return build_simulation_artifacts(fixture_simulated_tasks(), fixture_work_artifacts())
