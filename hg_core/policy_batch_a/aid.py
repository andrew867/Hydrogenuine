"""AID slice closure checks for Batch P1-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import aid_enabled, aid_require_evidence_for_capability
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_aid_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "ai_interaction_disclosure"
    checks.append(PolicyBatchCheck("aid_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "aid_ai_interaction_disclosure_gate.py"
    checks.append(PolicyBatchCheck("aid_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "aid"
    checks.append(PolicyBatchCheck("aid_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "aid_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "aid_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    integration = tests / "test_aid_integration.py"
    checks.append(
        PolicyBatchCheck(
            "aid_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "AID_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "aid_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    aid_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        aid_in_registry = "AID_DISCLOSURE_CREATED" in text
    checks.append(
        PolicyBatchCheck(
            "aid_rtc_types_registered",
            aid_in_registry,
            "AID_* in event_types_v1.yaml",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "aid_require_evidence_default",
            aid_require_evidence_for_capability(),
            "HG_AID_REQUIRE_EVIDENCE_FOR_CAPABILITY_CLAIMS=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "aid_disabled_by_default",
            not aid_enabled(),
            "HG_AID_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "aid",
        "feature": "AID",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_aid_closure_checks"]
