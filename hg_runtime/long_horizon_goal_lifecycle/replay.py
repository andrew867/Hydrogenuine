"""LHRE-01 / CAGI-54 replay — deterministic re-derivation of goal lifecycle artifacts."""

from __future__ import annotations

from hg_runtime.long_horizon_goal_lifecycle.artifact_writer import build_goal_lifecycle_artifacts
from hg_runtime.long_horizon_goal_lifecycle.fixtures import (
    fixture_checkpoints,
    fixture_long_horizon_goals,
    fixture_milestones,
    fixture_pause_resume_records,
)


def replay_goal_lifecycle_artifacts() -> dict:
    return build_goal_lifecycle_artifacts(
        fixture_long_horizon_goals(),
        fixture_milestones(),
        fixture_checkpoints(),
        fixture_pause_resume_records(),
    )
