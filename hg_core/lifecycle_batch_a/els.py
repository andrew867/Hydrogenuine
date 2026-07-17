"""ELS slice closure checks for Batch L3-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.emergence.config import els_enabled
from hg_runtime.emergence.profiles import get_profile


def run_els_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "emergence"
    checks.append(PolicyBatchCheck("els_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "els_emergence_gate.py"
    checks.append(PolicyBatchCheck("els_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "els"
    checks.append(PolicyBatchCheck("els_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "emergence_lifecycle" / "ELS_SPEC.md"
    checks.append(PolicyBatchCheck("els_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    try:
        crr_profile = get_profile("crr_reentry")
        checks.append(
            PolicyBatchCheck(
                "els_crr_reentry_profile_present",
                "crr_status_loaded" in crr_profile.required_checks,
                "crr_reentry profile",
            )
        )
    except KeyError:
        checks.append(
            PolicyBatchCheck("els_crr_reentry_profile_present", False, "missing crr_reentry profile")
        )

    checks.append(
        PolicyBatchCheck(
            "els_disabled_by_default",
            not els_enabled(),
            "HG_ELS_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "els",
        "feature": "ELS",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_els_closure_checks"]
