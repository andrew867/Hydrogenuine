"""CDO slice closure checks for Batch P1-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import cdo_enabled, cdo_unknown_to_safe_mode
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_cdo_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "compromised_disconnected_operation"
    checks.append(PolicyBatchCheck("cdo_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "cdo_compromised_disconnected_gate.py"
    checks.append(PolicyBatchCheck("cdo_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "cdo"
    checks.append(PolicyBatchCheck("cdo_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "cdo_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "cdo_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    replay_audit = module / "replay_audit.py"
    checks.append(
        PolicyBatchCheck(
            "cdo_replay_audit_present",
            replay_audit.is_file(),
            str(replay_audit.relative_to(workspace)),
        )
    )
    integration = tests / "test_cdo_integration.py"
    checks.append(
        PolicyBatchCheck(
            "cdo_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "CDO_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "cdo_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    cdo_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        cdo_in_registry = "CDO_COMPROMISE_SIGNAL_RECEIVED" in text
    checks.append(
        PolicyBatchCheck(
            "cdo_rtc_types_registered",
            cdo_in_registry,
            "CDO_* in event_types_v1.yaml",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "cdo_unknown_to_safe_mode_default",
            cdo_unknown_to_safe_mode(),
            "HG_CDO_UNKNOWN_TO_SAFE_MODE=1",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "cdo_disabled_by_default",
            not cdo_enabled(),
            "HG_CDO_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "cdo",
        "feature": "CDO",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_cdo_closure_checks"]
