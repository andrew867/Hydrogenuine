"""AEC-01 / CAGI-48 experiment engine — runs sandbox experiments from fixture data."""

from __future__ import annotations

from hg_runtime.active_experiment_harness.schemas import (
    EXPERIMENT_STATUS_SANDBOX,
    PLAN_STATUS_DRAFT,
    RESULT_STATUS_FIXTURE,
    ActiveExperimentHarnessError,
    reject_live_experiment,
)


def validate_experiment_plan(plan: dict) -> list[str]:
    issues = []
    if not plan.get("hypothesis_id"):
        issues.append("missing_hypothesis_id")
    if not plan.get("controlled_variables"):
        issues.append("missing_controlled_variables")
    if not plan.get("safety_boundaries"):
        issues.append("missing_safety_boundaries")
    if plan.get("status") != PLAN_STATUS_DRAFT:
        issues.append("plan_status_must_be_draft")
    if plan.get("live_execution_enabled"):
        issues.append("live_execution_forbidden")
    reject_live_experiment(plan)
    return issues


def run_sandbox_experiment(plan: dict, fixture_outcomes: list[dict]) -> dict:
    reject_live_experiment(plan)
    if not plan.get("sandbox_only"):
        raise ActiveExperimentHarnessError("Experiment must be sandbox_only")
    return {
        "result_id": f"result-{plan['plan_id']}",
        "plan_id": plan["plan_id"],
        "status": RESULT_STATUS_FIXTURE,
        "sandbox_mode": EXPERIMENT_STATUS_SANDBOX,
        "outcomes": fixture_outcomes,
        "conclusion_is_truth": False,
        "live_execution_performed": False,
    }


def classify_variables(plan: dict) -> dict:
    variables = plan.get("controlled_variables", [])
    return {
        "independent": [v for v in variables if v.get("type") == "INDEPENDENT"],
        "dependent": [v for v in variables if v.get("type") == "DEPENDENT"],
        "controlled": [v for v in variables if v.get("type") == "CONTROLLED"],
        "confounding": [v for v in variables if v.get("type") == "CONFOUNDING"],
    }
