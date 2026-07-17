"""SIEW-02 / CAGI-64 replay."""

from __future__ import annotations

from hg_runtime.economic_task_review.artifact_writer import build_review_artifacts
from hg_runtime.economic_task_review.fixtures import (
    fixture_quality_criteria,
    fixture_review_records,
)


def replay_review_artifacts() -> dict:
    return build_review_artifacts(fixture_review_records(), fixture_quality_criteria())
