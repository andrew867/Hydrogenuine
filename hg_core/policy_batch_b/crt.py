"""CRT slice closure checks for Batch P1-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_safety.config import crt_enabled, crt_include_exceptions
from hg_core.policy_safety.no_authority import check_policy_import_fences


def run_crt_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "certification_evidence_pack"
    checks.append(PolicyBatchCheck("crt_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "crt_certification_evidence_gate.py"
    checks.append(PolicyBatchCheck("crt_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "crt"
    checks.append(PolicyBatchCheck("crt_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    rtc_bridge = module / "rtc_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "crt_rtc_bridge_present",
            rtc_bridge.is_file(),
            str(rtc_bridge.relative_to(workspace)),
        )
    )
    service = module / "service.py"
    checks.append(
        PolicyBatchCheck(
            "crt_service_present",
            service.is_file(),
            str(service.relative_to(workspace)),
        )
    )
    replay_audit = module / "replay_audit.py"
    checks.append(
        PolicyBatchCheck(
            "crt_replay_audit_present",
            replay_audit.is_file(),
            str(replay_audit.relative_to(workspace)),
        )
    )
    integration = tests / "test_crt_integration.py"
    checks.append(
        PolicyBatchCheck(
            "crt_integration_tests_present",
            integration.is_file(),
            str(integration.relative_to(workspace)),
        )
    )
    impl_audit = workspace / "docs" / "reports" / "phases" / "CRT_IMPLEMENTATION_AUDIT.md"
    checks.append(
        PolicyBatchCheck(
            "crt_implementation_audit_present",
            impl_audit.is_file(),
            str(impl_audit.relative_to(workspace)),
        )
    )

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    crt_in_registry = False
    if event_types.is_file():
        text = event_types.read_text(encoding="utf-8")
        crt_in_registry = "CRT_CERTIFICATION_SNAPSHOT_REQUESTED" in text
    checks.append(
        PolicyBatchCheck(
            "crt_rtc_types_registered",
            crt_in_registry,
            "CRT_* in event_types_v1.yaml",
        )
    )

    fences_ok, fence_detail = check_policy_import_fences()
    checks.append(PolicyBatchCheck("policy_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "crt_include_exceptions_default",
            crt_include_exceptions(),
            "HG_CRT_INCLUDE_EXCEPTIONS=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "crt_disabled_by_default",
            not crt_enabled(),
            "HG_CRT_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "crt",
        "feature": "CRT",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_crt_closure_checks"]
