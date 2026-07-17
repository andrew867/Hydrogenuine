"""P31 evaluation policy — defines what may be evaluated and what may not."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import (
    PROVIDER_MODE,
    TASK_FAMILIES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)


def create_evaluation_policy(
    *,
    task_families: frozenset[str] | None = None,
    fixture_source: str = "local_only",
    provider_mode: str = PROVIDER_MODE,
) -> dict[str, Any]:
    families = task_families or TASK_FAMILIES
    unknown = families - TASK_FAMILIES
    if unknown:
        raise EvaluationHarnessBoundaryError(f"unknown_task_families:{','.join(sorted(unknown))}")
    if provider_mode != PROVIDER_MODE:
        raise EvaluationHarnessBoundaryError(f"provider_mode_must_be_fixture_only:{provider_mode}")
    if fixture_source != "local_only":
        raise EvaluationHarnessBoundaryError(f"fixture_source_must_be_local_only:{fixture_source}")
    record = {
        "schema": "evaluation_policy_v1",
        "task_families": sorted(families),
        "fixture_source": fixture_source,
        "provider_mode": provider_mode,
        "evaluation_is_not_truth": True,
        "evaluation_is_not_competence": True,
        "benchmark_is_not_deployment_permission": True,
        "evaluation_treated_as_truth": False,
        "evaluation_treated_as_competence": False,
        "competence_claimed": False,
        "tool_authorization_granted": False,
        "live_external_side_effects_created": False,
    }
    assert_neutral(record)
    return with_hash(record, "policy_hash")
