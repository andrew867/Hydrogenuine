"""P31 task family matrix — maps families to fixtures and evaluation methods."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.schemas import TASK_FAMILIES, EvaluationHarnessBoundaryError


TASK_FAMILY_MATRIX = {
    "code_generation": {
        "description": "Small function generation from prompts",
        "fixture_source": "human_authored",
        "evaluation_method": "exact_match_and_property_check",
    },
    "summarization": {
        "description": "Text summarization preserving key terms",
        "fixture_source": "human_authored",
        "evaluation_method": "property_check",
    },
    "classification": {
        "description": "Category assignment from text",
        "fixture_source": "human_authored",
        "evaluation_method": "exact_match",
    },
    "boundary_enforcement": {
        "description": "Refusal of unauthorized actions",
        "fixture_source": "human_authored",
        "evaluation_method": "must_refuse_check",
    },
    "gate_output": {
        "description": "Gate verdict generation from inputs",
        "fixture_source": "derived_from_test",
        "evaluation_method": "schema_and_verdict_match",
    },
    "consolidation_doc": {
        "description": "Consolidation report generation",
        "fixture_source": "derived_from_test",
        "evaluation_method": "property_check",
    },
}


def get_family_spec(family_id: str) -> dict[str, Any]:
    if family_id not in TASK_FAMILIES:
        raise EvaluationHarnessBoundaryError(f"unknown_task_family:{family_id}")
    return {"family_id": family_id, **TASK_FAMILY_MATRIX[family_id]}


def get_coverage(fixture_families: list[str]) -> dict[str, Any]:
    covered = set(fixture_families) & TASK_FAMILIES
    uncovered = TASK_FAMILIES - covered
    unknown = set(fixture_families) - TASK_FAMILIES
    return {
        "covered": sorted(covered),
        "uncovered": sorted(uncovered),
        "unknown": sorted(unknown),
        "coverage_ratio": len(covered) / len(TASK_FAMILIES) if TASK_FAMILIES else 0,
        "coverage_is_not_competence": True,
    }
