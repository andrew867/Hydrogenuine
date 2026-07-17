"""P31 expected/observed result records — deterministic comparison."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import stable_hash, with_hash
from hg_runtime.evaluation_harness.schemas import (
    EVALUATION_RESULT_STATES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)


def create_expected_observed_record(
    *,
    task_id: str,
    model_id: str,
    expected_output: dict[str, Any],
    observed_output: dict[str, Any],
    expected_properties: list[str] | None = None,
) -> dict[str, Any]:
    props = expected_properties or []
    matched = [p for p in props if observed_output.get(p) == expected_output.get(p)]
    failed = [p for p in props if p not in matched]
    record = {
        "schema": "expected_observed_record_v1",
        "task_id": task_id,
        "model_id": model_id,
        "expected_hash": stable_hash(expected_output),
        "observed_hash": stable_hash(observed_output),
        "properties_matched": matched,
        "properties_failed": failed,
        "match_is_not_truth": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record)
