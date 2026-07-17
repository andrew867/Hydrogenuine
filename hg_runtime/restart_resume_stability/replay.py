"""LHRE-02 / CAGI-55 replay — deterministic re-derivation of restart artifacts."""

from __future__ import annotations

from hg_runtime.restart_resume_stability.artifact_writer import build_restart_artifacts
from hg_runtime.restart_resume_stability.fixtures import (
    fixture_restart_snapshots,
    fixture_resume_attempts,
)


def replay_restart_artifacts() -> dict:
    return build_restart_artifacts(
        fixture_restart_snapshots(),
        fixture_resume_attempts(),
    )
