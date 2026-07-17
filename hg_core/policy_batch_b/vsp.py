"""VSP slice closure checks for Batch P1-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import vsp_enabled, vsp_minor_strict_mode
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_vsp_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "vulnerable_subject_protection"
    checks.append(PolicyBatchCheck("vsp_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "vsp_vulnerable_subject_gate.py"
    checks.append(PolicyBatchCheck("vsp_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "vsp"
    checks.append(PolicyBatchCheck("vsp_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "vsp_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "vsp_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    replay_audit = module / "replay_audit.py"
    checks.append(
        PolicyBatchCheck(
            "vsp_replay_audit_present",
            replay_audit.is_file(),
            str(replay_audit.relative_to(workspace)),
        )
    )
    routing = module / "routing.py"
    checks.append(
        PolicyBatchCheck(
            "vsp_routing_present",
            routing.is_file(),
            str(routing.relative_to(workspace)),
        )
    )
    integration = tests / "test_vsp_integration.py"
    checks.append(
        PolicyBatchCheck(
            "vsp_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "VSP_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "vsp_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    vsp_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        vsp_in_registry = "VSP_SIGNAL_RECEIVED" in text
    checks.append(
        PolicyBatchCheck(
            "vsp_rtc_types_registered",
            vsp_in_registry,
            "VSP_* in event_types_v1.yaml",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "vsp_minor_strict_default",
            vsp_minor_strict_mode(),
            "HG_VSP_MINOR_STRICT_MODE=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "vsp_disabled_by_default",
            not vsp_enabled(),
            "HG_VSP_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "vsp",
        "feature": "VSP",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_vsp_closure_checks"]
