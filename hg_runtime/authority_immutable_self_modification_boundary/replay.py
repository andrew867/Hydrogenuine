"""BSI-03 / CAGI-62 replay."""

from __future__ import annotations

from hg_runtime.authority_immutable_self_modification_boundary.artifact_writer import (
    build_boundary_artifacts,
)
from hg_runtime.authority_immutable_self_modification_boundary.fixtures import (
    fixture_all_bad_mutations,
    fixture_boundary_record,
)


def replay_boundary_artifacts() -> dict:
    return build_boundary_artifacts(
        fixture_boundary_record(),
        fixture_all_bad_mutations(),
    )
