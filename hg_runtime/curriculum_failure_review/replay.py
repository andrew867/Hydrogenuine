"""AEC-05 / CAGI-52 replay — deterministic re-derivation of failure review artifacts."""

from __future__ import annotations

from hg_runtime.curriculum_failure_review.artifact_writer import build_failure_review_artifacts
from hg_runtime.curriculum_failure_review.fixtures import (
    fixture_failure_records,
    fixture_failure_reviews,
    fixture_root_cause_hypotheses,
)


def replay_failure_review_artifacts() -> dict:
    return build_failure_review_artifacts(
        fixture_failure_records(),
        fixture_root_cause_hypotheses(),
        fixture_failure_reviews(),
    )
