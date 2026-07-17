"""F02 state-space memory organ replay."""

from __future__ import annotations

from hg_runtime.state_space_memory.artifact_writer import build_state_space_artifacts
from hg_runtime.state_space_memory.fixtures import (
    fixture_compressed_trajectory,
    fixture_repair_recommendation,
    fixture_stable_run_snapshots,
    fixture_state_query,
    fixture_state_transition,
)


def replay_state_space_artifacts() -> dict:
    snapshots = fixture_stable_run_snapshots()
    transitions = [
        fixture_state_transition(1, 2),
        fixture_state_transition(2, 3),
    ]
    return build_state_space_artifacts(
        snapshots,
        transitions,
        [fixture_compressed_trajectory()],
        [fixture_repair_recommendation()],
        [fixture_state_query()],
    )
