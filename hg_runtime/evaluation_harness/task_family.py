"""P31 task family definitions — bounded evaluation categories."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import (
    TASK_FAMILIES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)


def create_task_family(
    *,
    family_id: str,
    description: str,
    fixture_source: str = "human_authored",
    evaluation_method: str = "property_check",
) -> dict[str, Any]:
    if family_id not in TASK_FAMILIES:
        raise EvaluationHarnessBoundaryError(f"unknown_task_family:{family_id}")
    if fixture_source not in ("human_authored", "derived_from_test", "synthetic"):
        raise EvaluationHarnessBoundaryError(f"unknown_fixture_source:{fixture_source}")
    record = {
        "schema": "task_family_v1",
        "family_id": family_id,
        "description": description,
        "fixture_source": fixture_source,
        "evaluation_method": evaluation_method,
        "family_is_not_general_competence": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record)
