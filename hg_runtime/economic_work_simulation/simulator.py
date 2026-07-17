"""SIEW-01 / CAGI-63 simulator — creates and validates simulated work."""

from __future__ import annotations

from hg_runtime.economic_work_simulation.schemas import (
    TASK_DOMAINS,
    EconomicWorkSimulationError,
    reject_real_economic_work,
)


def validate_task(task: dict) -> list[str]:
    issues = []
    if not task.get("task_id"):
        issues.append("missing_task_id")
    if task.get("domain") not in TASK_DOMAINS:
        issues.append("invalid_domain")
    if not task.get("simulation_only"):
        issues.append("must_be_simulation_only")
    if task.get("real_customer"):
        issues.append("real_customer_forbidden")
    if task.get("real_payment"):
        issues.append("real_payment_forbidden")
    val = task.get("estimated_value", {})
    if not val.get("advisory_only"):
        issues.append("value_must_be_advisory_only")
    reject_real_economic_work(task)
    return issues


def validate_artifact(artifact: dict) -> list[str]:
    issues = []
    if not artifact.get("artifact_id"):
        issues.append("missing_artifact_id")
    if not artifact.get("task_id"):
        issues.append("missing_task_id")
    if not artifact.get("simulated"):
        issues.append("must_be_simulated")
    return issues
