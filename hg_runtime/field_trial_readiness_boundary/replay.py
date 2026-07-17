"""P69 field trial readiness boundary replay."""

from __future__ import annotations

from hg_runtime.field_trial_readiness_boundary.artifact_writer import build_readiness_artifacts
from hg_runtime.field_trial_readiness_boundary.fixtures import (
    fixture_candidate_field_scenario,
    fixture_field_readiness_checklist,
    fixture_readiness_gap,
    fixture_rehearsal_record,
)


def replay_readiness_artifacts() -> dict:
    return build_readiness_artifacts(
        [fixture_field_readiness_checklist()],
        [fixture_candidate_field_scenario()],
        [fixture_rehearsal_record()],
        [fixture_readiness_gap()],
    )
