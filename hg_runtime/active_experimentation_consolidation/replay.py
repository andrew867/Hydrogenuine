"""AEC-06 / CAGI-53 replay — deterministic re-derivation of consolidation artifacts."""

from __future__ import annotations

from hg_runtime.active_experimentation_consolidation.artifact_writer import (
    build_consolidation_artifacts,
)
from hg_runtime.active_experimentation_consolidation.fixtures import (
    fixture_integration_checks,
    fixture_phase_stats,
    fixture_phase_verdicts,
)


def replay_consolidation_artifacts() -> dict:
    return build_consolidation_artifacts(
        fixture_phase_verdicts(),
        fixture_phase_stats(),
        fixture_integration_checks(),
    )
