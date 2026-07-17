"""Whole-organism fixture soak replay."""

from __future__ import annotations

from hg_runtime.whole_organism_soak.artifact_writer import build_soak_artifacts
from hg_runtime.whole_organism_soak.harness import run_fixture_soak


def replay_soak_artifacts() -> dict:
    return build_soak_artifacts(run_fixture_soak())
