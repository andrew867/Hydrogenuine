"""SML closure checks for Batch S5-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.batch_checks import signaling_rtc_design_checks
from hg_core.signaling.config import (
    sml_enabled,
    sml_refuse_bypass_hypothesis,
    sml_refuse_compliance_optimization,
    sml_refuse_stale_cycle,
    sml_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.self_maximization_loop.events import planned_sml_event_refs


def run_sml_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "self_maximization_loop"
    checks.append(PolicyBatchCheck("sml_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "sml_self_maximization_gate.py"
    checks.append(PolicyBatchCheck("sml_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "sml"
    checks.append(PolicyBatchCheck("sml_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "self_maximization_loop" / "SML_SPEC.md"
    checks.append(PolicyBatchCheck("sml_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        signaling_rtc_design_checks(
            prefix="sml",
            events=planned_sml_event_refs(),
            minimum_events=15,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "sml_static_fixtures_only_default",
            sml_static_fixtures_only(),
            "HG_SML_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sml_refuse_stale_cycle_default",
            sml_refuse_stale_cycle(),
            "HG_SML_REFUSE_STALE_CYCLE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sml_refuse_bypass_hypothesis_default",
            sml_refuse_bypass_hypothesis(),
            "HG_SML_REFUSE_BYPASS_HYPOTHESIS=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sml_refuse_compliance_optimization_default",
            sml_refuse_compliance_optimization(),
            "HG_SML_REFUSE_COMPLIANCE_OPTIMIZATION=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "sml_disabled_by_default",
            not sml_enabled(),
            "HG_SML_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "sml",
        "feature": "SML",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_sml_closure_checks"]
