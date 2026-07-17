"""LHRE-06 / CAGI-59 replay."""

from __future__ import annotations

from hg_runtime.long_horizon_reliability_consolidation.artifact_writer import build_consolidation_artifacts
from hg_runtime.long_horizon_reliability_consolidation.fixtures import (
    fixture_phase_gate_results,
    fixture_tranche_summary,
)


def replay_consolidation_artifacts() -> dict:
    return build_consolidation_artifacts(
        fixture_tranche_summary(),
        fixture_phase_gate_results(),
    )
