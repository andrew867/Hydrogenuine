"""P31 evaluation result — records outcome without claiming truth."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import (
    EVALUATION_RESULT_STATES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)


def create_evaluation_result(
    *,
    task_id: str,
    task_family: str,
    model_id: str,
    state: str,
    properties_matched: list[str] | None = None,
    properties_failed: list[str] | None = None,
    boundary_violations: list[str] | None = None,
) -> dict[str, Any]:
    if state not in EVALUATION_RESULT_STATES:
        raise EvaluationHarnessBoundaryError(f"unknown_result_state:{state}")
    record = {
        "schema": "evaluation_result_v1",
        "task_id": task_id,
        "task_family": task_family,
        "model_id": model_id,
        "state": state,
        "properties_matched": properties_matched or [],
        "properties_failed": properties_failed or [],
        "boundary_violations": boundary_violations or [],
        "evaluation_is_not_competence": True,
        "competence_claimed": False,
        "evaluation_treated_as_truth": False,
    }
    assert_neutral(record)
    return with_hash(record, "result_hash")
