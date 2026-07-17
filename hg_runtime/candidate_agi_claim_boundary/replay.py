"""P71 candidate-AGI claim boundary replay."""

from __future__ import annotations

from hg_runtime.candidate_agi_claim_boundary.artifact_writer import build_claim_boundary_artifacts
from hg_runtime.candidate_agi_claim_boundary.fixtures import (
    fixture_capability_matrix,
    fixture_claim_boundary_record,
    fixture_known_debt_register,
    fixture_public_safe_summary,
)


def replay_claim_boundary_artifacts() -> dict:
    return build_claim_boundary_artifacts(
        [fixture_capability_matrix()],
        [fixture_claim_boundary_record()],
        [fixture_known_debt_register()],
        [fixture_public_safe_summary()],
    )
