"""AEC-01 / CAGI-48 artifact writer — builds experiment receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.active_experiment_harness.experiment_engine import (
    classify_variables,
    run_sandbox_experiment,
    validate_experiment_plan,
)
from hg_runtime.active_experiment_harness.safety_boundary import (
    enforce_sandbox_only,
    validate_safety_boundaries,
)
from hg_runtime.active_experiment_harness.schemas import (
    EXPERIMENT_IS_NOT_ACTION,
    PLAN_IS_NOT_PERMISSION,
    RESULT_IS_NOT_TRUTH,
    SANDBOX_IS_NOT_LIVE,
    reject_live_experiment,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_experiment_artifacts(
    hypotheses: list[dict],
    plans: list[dict],
    fixture_outcomes: list[list[dict]] | None = None,
) -> dict:
    if fixture_outcomes is None:
        fixture_outcomes = [[] for _ in plans]

    validated_plans = []
    plan_issues = []
    for plan in plans:
        issues = validate_experiment_plan(plan)
        safety_issues = validate_safety_boundaries(plan)
        validated_plans.append({
            "plan": plan,
            "valid": not issues and not safety_issues,
            "issues": issues + safety_issues,
            "variables": classify_variables(plan),
        })
        plan_issues.extend(issues + safety_issues)

    results = []
    for plan, outcomes in zip(plans, fixture_outcomes):
        if outcomes:
            result = run_sandbox_experiment(plan, outcomes)
            enforce_sandbox_only(result)
            results.append(result)

    artifacts = {
        "hypotheses": hypotheses,
        "hypothesis_count": len(hypotheses),
        "plans": validated_plans,
        "plan_count": len(validated_plans),
        "results": results,
        "result_count": len(results),
        "all_sandbox_only": all(r.get("sandbox_mode") == "SANDBOX_ONLY" for r in results),
        "all_conclusions_not_truth": all(not r.get("conclusion_is_truth") for r in results),
        "no_live_execution": all(not r.get("live_execution_performed") for r in results),
        "plan_issues": plan_issues,
        "boundary_assertions": {
            "experiment_is_not_action": EXPERIMENT_IS_NOT_ACTION,
            "sandbox_is_not_live": SANDBOX_IS_NOT_LIVE,
            "result_is_not_truth": RESULT_IS_NOT_TRUTH,
            "plan_is_not_permission": PLAN_IS_NOT_PERMISSION,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    hits = []
    for pattern in ("sk-", "api_key=", "Bearer ", "token=", "password="):
        if pattern.lower() in text.lower():
            hits.append(pattern)
    return hits
