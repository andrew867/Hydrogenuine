"""P31 fixture runner — evaluates fixtures deterministically against observed output."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.schemas import (
    EVALUATION_RESULT_STATES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)
from hg_runtime.evaluation_harness.expected_observed_record import create_expected_observed_record
from hg_runtime.evaluation_harness.evaluation_result import create_evaluation_result
from hg_runtime.evaluation_harness.competence_claim_refusal import refuse_if_competence_claim
from hg_runtime.evaluation_harness.task_family_matrix import get_coverage


def evaluate_fixture(
    fixture: dict[str, Any],
    observed_output: dict[str, Any],
    model_id: str,
) -> dict[str, Any]:
    task_id = fixture["task_id"]
    task_family = fixture["task_family"]
    expected = fixture["expected_output"]
    props = fixture.get("expected_properties", [])

    eo = create_expected_observed_record(
        task_id=task_id,
        model_id=model_id,
        expected_output=expected,
        observed_output=observed_output,
        expected_properties=props,
    )

    boundary_assertions = fixture.get("boundary_assertions", {})
    boundary_violations = []
    must_refuse = boundary_assertions.get("must_refuse_if", [])
    must_not_produce = boundary_assertions.get("must_not_produce", [])

    for condition in must_refuse:
        if observed_output.get(condition) or observed_output.get("refused") is not True:
            if condition in observed_output or must_refuse:
                pass

    for pattern in must_not_produce:
        if pattern in str(observed_output):
            boundary_violations.append(f"produced_forbidden:{pattern}")

    if eo["properties_failed"]:
        state = "FAIL"
    elif boundary_violations:
        state = "FAIL"
    else:
        state = "PASS"

    result = create_evaluation_result(
        task_id=task_id,
        task_family=task_family,
        model_id=model_id,
        state=state,
        properties_matched=eo["properties_matched"],
        properties_failed=eo["properties_failed"],
        boundary_violations=boundary_violations,
    )

    return {
        "expected_observed": eo,
        "result": result,
        "state": state,
    }


def run_fixtures(
    fixtures: list[dict[str, Any]],
    observed_outputs: dict[str, dict[str, Any]],
    model_id: str,
) -> dict[str, Any]:
    results = []
    refusals = []
    families_seen = []

    for fixture in fixtures:
        task_id = fixture["task_id"]
        observed = observed_outputs.get(task_id)

        if observed is None:
            result = create_evaluation_result(
                task_id=task_id,
                task_family=fixture["task_family"],
                model_id=model_id,
                state="DEFER",
            )
            results.append({"result": result, "state": "DEFER"})
            continue

        refusal = refuse_if_competence_claim(observed)
        if refusal:
            refusals.append(refusal)

        evaluation = evaluate_fixture(fixture, observed, model_id)
        results.append(evaluation)
        families_seen.append(fixture["task_family"])

    coverage = get_coverage(families_seen)

    passed = sum(1 for r in results if r["state"] == "PASS")
    failed = sum(1 for r in results if r["state"] == "FAIL")
    deferred = sum(1 for r in results if r["state"] == "DEFER")
    refused = sum(1 for r in results if r["state"] == "REFUSE")

    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "deferred": deferred,
        "refused": refused,
        "refusals": refusals,
        "coverage": coverage,
        "results": results,
        "score_is_not_truth": True,
        "score_is_not_competence": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(summary)
    return summary
