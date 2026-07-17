"""GCB closure checks for Batch C6-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.batch_checks import control_rtc_design_checks
from hg_core.control_cluster.config import (
    gcb_static_fixtures_only,
    gcb_refuse_stale_goal,
    gcb_refuse_goal_as_permission,
    gcb_enabled,
)
from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.goal_commitment_boundary.events import planned_gcb_event_refs


def run_gcb_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "goal_commitment_boundary"
    checks.append(PolicyBatchCheck("gcb_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "goal_commitment_boundary_gate.py"
    checks.append(PolicyBatchCheck("gcb_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "gcb"
    checks.append(PolicyBatchCheck("gcb_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "goal_commitment_boundary" / "GCB_SPEC.md"
    checks.append(PolicyBatchCheck("gcb_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        control_rtc_design_checks(
            prefix="gcb",
            events=planned_gcb_event_refs(),
            minimum_events=9,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "gcb_gcb_static_fixtures_only_default",
            gcb_static_fixtures_only(),
            "HG_GCB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "gcb_gcb_refuse_stale_goal_default",
            gcb_refuse_stale_goal(),
            "HG_GCB_REFUSE_STALE_GOAL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "gcb_gcb_refuse_goal_as_permission_default",
            gcb_refuse_goal_as_permission(),
            "HG_GCB_REFUSE_GOAL_AS_PERMISSION=1",
        )
    )

    fences_ok, fence_detail = check_control_import_fences()
    checks.append(
        PolicyBatchCheck("control_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "gcb_disabled_by_default",
            not gcb_enabled(),
            "HG_GCB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "gcb",
        "feature": "GCB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_gcb_closure_checks"]
