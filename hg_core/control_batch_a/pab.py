"""PAB closure checks for Batch C6-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.batch_checks import control_rtc_design_checks
from hg_core.control_cluster.config import (
    pab_static_fixtures_only,
    pab_refuse_stale_priority,
    pab_refuse_priority_as_permission,
    pab_enabled,
)
from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.priority_allocation_boundary.events import planned_pab_event_refs


def run_pab_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "priority_allocation_boundary"
    checks.append(PolicyBatchCheck("pab_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "priority_allocation_boundary_gate.py"
    checks.append(PolicyBatchCheck("pab_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "pab"
    checks.append(PolicyBatchCheck("pab_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "priority_allocation_boundary" / "PAB_SPEC.md"
    checks.append(PolicyBatchCheck("pab_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        control_rtc_design_checks(
            prefix="pab",
            events=planned_pab_event_refs(),
            minimum_events=7,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "pab_pab_static_fixtures_only_default",
            pab_static_fixtures_only(),
            "HG_PAB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pab_pab_refuse_stale_priority_default",
            pab_refuse_stale_priority(),
            "HG_PAB_REFUSE_STALE_PRIORITY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pab_pab_refuse_priority_as_permission_default",
            pab_refuse_priority_as_permission(),
            "HG_PAB_REFUSE_PRIORITY_AS_PERMISSION=1",
        )
    )

    fences_ok, fence_detail = check_control_import_fences()
    checks.append(
        PolicyBatchCheck("control_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "pab_disabled_by_default",
            not pab_enabled(),
            "HG_PAB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "pab",
        "feature": "PAB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_pab_closure_checks"]
