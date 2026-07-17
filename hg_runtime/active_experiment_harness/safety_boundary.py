"""AEC-01 / CAGI-48 safety boundary enforcement for experiments."""

from __future__ import annotations

from hg_runtime.active_experiment_harness.schemas import (
    SAFETY_BOUNDARY_TYPES,
    ActiveExperimentHarnessError,
)


def validate_safety_boundaries(plan: dict) -> list[str]:
    violations = []
    boundaries = plan.get("safety_boundaries", [])
    if not boundaries:
        violations.append("no_safety_boundaries_declared")
    if plan.get("live_execution_enabled"):
        violations.append("live_execution_forbidden")
    if plan.get("authorizes_tool"):
        violations.append("tool_authorization_forbidden")
    if plan.get("execute_externally"):
        violations.append("external_execution_forbidden")
    if plan.get("creates_live_effect"):
        violations.append("live_effects_forbidden")
    return violations


def enforce_sandbox_only(result: dict) -> None:
    if result.get("live_execution_performed"):
        raise ActiveExperimentHarnessError("Result claims live execution — boundary violation")
    if result.get("conclusion_is_truth"):
        raise ActiveExperimentHarnessError("Result claims truth — boundary violation")
