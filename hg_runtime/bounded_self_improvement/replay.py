"""BSI-01 / CAGI-60 replay."""

from __future__ import annotations

from hg_runtime.bounded_self_improvement.artifact_writer import build_proposal_artifacts
from hg_runtime.bounded_self_improvement.fixtures import (
    fixture_improvement_proposals,
    fixture_proposal_queue,
)


def replay_proposal_artifacts() -> dict:
    return build_proposal_artifacts(
        fixture_improvement_proposals(),
        fixture_proposal_queue(),
    )
