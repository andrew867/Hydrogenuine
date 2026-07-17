"""SYN slice closure checks for Batch P1-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import syn_enabled
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_syn_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "synthetic_content_provenance"
    checks.append(PolicyBatchCheck("syn_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "syn_synthetic_content_gate.py"
    checks.append(PolicyBatchCheck("syn_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "syn"
    checks.append(PolicyBatchCheck("syn_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "syn_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "syn_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    integration = tests / "test_syn_integration.py"
    checks.append(
        PolicyBatchCheck(
            "syn_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "SYN_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "syn_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    syn_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        syn_in_registry = "SYN_CONTENT_ARTIFACT_REGISTERED" in text
    checks.append(
        PolicyBatchCheck(
            "syn_rtc_types_registered",
            syn_in_registry,
            "SYN_* in event_types_v1.yaml",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "syn_disabled_by_default",
            not syn_enabled(),
            "HG_SYN_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "syn",
        "feature": "SYN",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_syn_closure_checks"]
