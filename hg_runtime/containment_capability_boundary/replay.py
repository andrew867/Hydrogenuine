"""CLIFT-02 / CAGI-67 replay."""

from __future__ import annotations

from hg_runtime.containment_capability_boundary.artifact_writer import build_containment_artifacts
from hg_runtime.containment_capability_boundary.fixtures import (
    fixture_capability_declarations,
    fixture_containment_mode_record,
    fixture_containment_status_snapshot,
)


def replay_containment_artifacts() -> dict:
    return build_containment_artifacts(
        fixture_capability_declarations(),
        fixture_containment_mode_record(),
        fixture_containment_status_snapshot(),
    )
