"""DMI slice closure checks for Batch P1-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import dmi_election_always_review, dmi_enabled
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_dmi_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "democratic_misinformation_integrity"
    checks.append(PolicyBatchCheck("dmi_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "dmi_democratic_integrity_gate.py"
    checks.append(PolicyBatchCheck("dmi_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "dmi"
    checks.append(PolicyBatchCheck("dmi_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "dmi_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "dmi_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    integration = tests / "test_dmi_integration.py"
    checks.append(
        PolicyBatchCheck(
            "dmi_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "DMI_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "dmi_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    dmi_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        dmi_in_registry = "DMI_PUBLIC_INFLUENCE_SIGNAL_RECEIVED" in text
    checks.append(
        PolicyBatchCheck(
            "dmi_rtc_types_registered",
            dmi_in_registry,
            "DMI_* in event_types_v1.yaml",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "dmi_election_always_review_default",
            dmi_election_always_review(),
            "HG_DMI_ELECTION_ALWAYS_REVIEW=1",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "dmi_disabled_by_default",
            not dmi_enabled(),
            "HG_DMI_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "dmi",
        "feature": "DMI",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_dmi_closure_checks"]
