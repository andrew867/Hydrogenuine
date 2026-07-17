"""AEC-02 / CAGI-49 replay — deterministic re-derivation of curriculum artifacts."""

from __future__ import annotations

from hg_runtime.sandbox_curriculum.artifact_writer import build_curriculum_artifacts
from hg_runtime.sandbox_curriculum.fixtures import (
    fixture_curriculum_scores,
    fixture_curriculum_tasks,
    fixture_task_sequences,
)


def replay_curriculum_artifacts() -> dict:
    return build_curriculum_artifacts(
        fixture_curriculum_tasks(),
        fixture_task_sequences(),
        fixture_curriculum_scores(),
    )
