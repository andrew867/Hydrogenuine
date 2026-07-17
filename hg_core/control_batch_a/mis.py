"""MIS closure checks for Batch C6-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.batch_checks import control_rtc_design_checks
from hg_core.control_cluster.config import (
    mis_static_fixtures_only,
    mis_refuse_stale_drift,
    mis_refuse_goal_as_authority,
    mis_enabled,
)
from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.mission_drift_boundary.events import planned_mis_event_refs


def run_mis_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "mission_drift_boundary"
    checks.append(PolicyBatchCheck("mis_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "mission_drift_boundary_gate.py"
    checks.append(PolicyBatchCheck("mis_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "mis"
    checks.append(PolicyBatchCheck("mis_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "mission_drift_boundary" / "MIS_SPEC.md"
    checks.append(PolicyBatchCheck("mis_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        control_rtc_design_checks(
            prefix="mis",
            events=planned_mis_event_refs(),
            minimum_events=7,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "mis_mis_static_fixtures_only_default",
            mis_static_fixtures_only(),
            "HG_MIS_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "mis_mis_refuse_stale_drift_default",
            mis_refuse_stale_drift(),
            "HG_MIS_REFUSE_STALE_DRIFT=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "mis_mis_refuse_goal_as_authority_default",
            mis_refuse_goal_as_authority(),
            "HG_MIS_REFUSE_GOAL_AS_AUTHORITY=1",
        )
    )

    fences_ok, fence_detail = check_control_import_fences()
    checks.append(
        PolicyBatchCheck("control_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "mis_disabled_by_default",
            not mis_enabled(),
            "HG_MIS_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "mis",
        "feature": "MIS",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_mis_closure_checks"]
