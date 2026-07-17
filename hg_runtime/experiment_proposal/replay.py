"""AEC-04 / CAGI-51 replay — deterministic re-derivation of proposal artifacts."""

from __future__ import annotations

from hg_runtime.experiment_proposal.artifact_writer import build_proposal_artifacts
from hg_runtime.experiment_proposal.fixtures import (
    fixture_proposal_reviews,
    fixture_proposals,
)


def replay_proposal_artifacts() -> dict:
    return build_proposal_artifacts(fixture_proposals(), fixture_proposal_reviews())
