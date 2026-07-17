"""CLIFT-03 / CAGI-68 replay."""

from __future__ import annotations

from hg_runtime.local_inference_operations.artifact_writer import build_inference_artifacts
from hg_runtime.local_inference_operations.fixtures import (
    fixture_inference_status_snapshot,
    fixture_model_registry,
    fixture_output_boundary_record,
)


def replay_inference_artifacts() -> dict:
    return build_inference_artifacts(
        fixture_model_registry(),
        [fixture_output_boundary_record()],
        fixture_inference_status_snapshot(),
    )
