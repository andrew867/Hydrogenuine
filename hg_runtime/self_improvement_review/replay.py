"""BSI-02 / CAGI-61 replay."""

from __future__ import annotations

from hg_runtime.self_improvement_review.artifact_writer import build_review_artifacts
from hg_runtime.self_improvement_review.fixtures import (
    fixture_evaluation_criteria,
    fixture_review_records,
)


def replay_review_artifacts() -> dict:
    return build_review_artifacts(
        fixture_review_records(),
        fixture_evaluation_criteria(),
    )
