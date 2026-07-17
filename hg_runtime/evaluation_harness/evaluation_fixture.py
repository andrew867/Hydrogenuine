"""P31 evaluation fixture — bounded test input/expected output pairs."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import (
    TASK_FAMILIES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)


def create_evaluation_fixture(
    *,
    task_family: str,
    task_id: str,
    input_data: dict[str, Any],
    expected_output: dict[str, Any],
    expected_properties: list[str] | None = None,
    boundary_assertions: dict[str, list[str]] | None = None,
    source: str = "human_authored",
) -> dict[str, Any]:
    if task_family not in TASK_FAMILIES:
        raise EvaluationHarnessBoundaryError(f"unknown_task_family:{task_family}")
    if source not in ("human_authored", "derived_from_test", "synthetic"):
        raise EvaluationHarnessBoundaryError(f"unknown_fixture_source:{source}")
    record = {
        "schema": "evaluation_fixture_v1",
        "task_family": task_family,
        "task_id": task_id,
        "input": input_data,
        "expected_output": expected_output,
        "expected_properties": expected_properties or [],
        "boundary_assertions": boundary_assertions or {"must_refuse_if": [], "must_not_produce": []},
        "source": source,
        "fixture_is_not_truth": True,
        "evaluation_treated_as_truth": False,
    }
    assert_neutral(record)
    return with_hash(record, "fixture_hash")
