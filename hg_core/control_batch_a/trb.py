"""TRB closure checks for Batch C6-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.batch_checks import control_rtc_design_checks
from hg_core.control_cluster.config import (
    trb_static_fixtures_only,
    trb_refuse_stale_trust,
    trb_refuse_trust_as_truth,
    trb_enabled,
)
from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.trust_boundary_calibration.events import planned_trb_event_refs


def run_trb_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "trust_boundary_calibration"
    checks.append(PolicyBatchCheck("trb_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "trust_boundary_calibration_gate.py"
    checks.append(PolicyBatchCheck("trb_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "trb"
    checks.append(PolicyBatchCheck("trb_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "trust_boundary_calibration" / "TRB_SPEC.md"
    checks.append(PolicyBatchCheck("trb_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        control_rtc_design_checks(
            prefix="trb",
            events=planned_trb_event_refs(),
            minimum_events=7,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "trb_trb_static_fixtures_only_default",
            trb_static_fixtures_only(),
            "HG_TRB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "trb_trb_refuse_stale_trust_default",
            trb_refuse_stale_trust(),
            "HG_TRB_REFUSE_STALE_TRUST=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "trb_trb_refuse_trust_as_truth_default",
            trb_refuse_trust_as_truth(),
            "HG_TRB_REFUSE_TRUST_AS_TRUTH=1",
        )
    )

    fences_ok, fence_detail = check_control_import_fences()
    checks.append(
        PolicyBatchCheck("control_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "trb_disabled_by_default",
            not trb_enabled(),
            "HG_TRB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "trb",
        "feature": "TRB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_trb_closure_checks"]
