"""FCE slice closure checks for Batch P1-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import fce_enabled, fce_fail_closed
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_fce_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "frontier_capability_evaluation"
    checks.append(PolicyBatchCheck("fce_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "fce_frontier_capability_gate.py"
    checks.append(PolicyBatchCheck("fce_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "fce"
    checks.append(PolicyBatchCheck("fce_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "fce_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "fce_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    integration = tests / "test_fce_integration.py"
    checks.append(
        PolicyBatchCheck(
            "fce_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "FCE_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "fce_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    fce_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        fce_in_registry = "FCE_SIGNAL_RECEIVED" in text
    checks.append(
        PolicyBatchCheck(
            "fce_rtc_types_registered",
            fce_in_registry,
            "FCE_* in event_types_v1.yaml",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "fce_fail_closed_default",
            fce_fail_closed(),
            "HG_FCE_FAIL_CLOSED=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "fce_disabled_by_default",
            not fce_enabled(),
            "HG_FCE_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "fce",
        "feature": "FCE",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_fce_closure_checks"]
