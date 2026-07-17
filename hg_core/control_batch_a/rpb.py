"""RPB closure checks for Batch C6-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.batch_checks import control_rtc_design_checks
from hg_core.control_cluster.config import (
    rpb_static_fixtures_only,
    rpb_refuse_stale_posture,
    rpb_refuse_posture_as_execution,
    rpb_enabled,
)
from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.risk_posture_boundary.events import planned_rpb_event_refs


def run_rpb_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "risk_posture_boundary"
    checks.append(PolicyBatchCheck("rpb_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "risk_posture_boundary_gate.py"
    checks.append(PolicyBatchCheck("rpb_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "rpb"
    checks.append(PolicyBatchCheck("rpb_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "risk_posture_boundary" / "RPB_SPEC.md"
    checks.append(PolicyBatchCheck("rpb_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        control_rtc_design_checks(
            prefix="rpb",
            events=planned_rpb_event_refs(),
            minimum_events=11,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "rpb_rpb_static_fixtures_only_default",
            rpb_static_fixtures_only(),
            "HG_RPB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rpb_rpb_refuse_stale_posture_default",
            rpb_refuse_stale_posture(),
            "HG_RPB_REFUSE_STALE_POSTURE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rpb_rpb_refuse_posture_as_execution_default",
            rpb_refuse_posture_as_execution(),
            "HG_RPB_REFUSE_POSTURE_AS_EXECUTION=1",
        )
    )

    fences_ok, fence_detail = check_control_import_fences()
    checks.append(
        PolicyBatchCheck("control_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "rpb_disabled_by_default",
            not rpb_enabled(),
            "HG_RPB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rpb",
        "feature": "RPB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_rpb_closure_checks"]
