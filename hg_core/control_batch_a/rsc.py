"""RSC closure checks for Batch C6-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.batch_checks import control_rtc_design_checks
from hg_core.control_cluster.config import (
    rsc_static_fixtures_only,
    rsc_refuse_stale_posture,
    rsc_refuse_safety_bypass,
    rsc_enabled,
)
from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.resource_scarcity_controller.events import planned_rsc_event_refs


def run_rsc_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "resource_scarcity_controller"
    checks.append(PolicyBatchCheck("rsc_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "resource_scarcity_controller_gate.py"
    checks.append(PolicyBatchCheck("rsc_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "rsc"
    checks.append(PolicyBatchCheck("rsc_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "resource_scarcity_controller" / "RSC_SPEC.md"
    checks.append(PolicyBatchCheck("rsc_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        control_rtc_design_checks(
            prefix="rsc",
            events=planned_rsc_event_refs(),
            minimum_events=8,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "rsc_rsc_static_fixtures_only_default",
            rsc_static_fixtures_only(),
            "HG_RSC_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rsc_rsc_refuse_stale_posture_default",
            rsc_refuse_stale_posture(),
            "HG_RSC_REFUSE_STALE_POSTURE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rsc_rsc_refuse_safety_bypass_default",
            rsc_refuse_safety_bypass(),
            "HG_RSC_REFUSE_SAFETY_BYPASS=1",
        )
    )

    fences_ok, fence_detail = check_control_import_fences()
    checks.append(
        PolicyBatchCheck("control_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "rsc_disabled_by_default",
            not rsc_enabled(),
            "HG_RSC_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rsc",
        "feature": "RSC",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_rsc_closure_checks"]
