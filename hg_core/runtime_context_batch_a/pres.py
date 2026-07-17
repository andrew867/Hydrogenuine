"""PRES slice closure checks for Batch R2-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import pres_enabled, pres_require_authority_badge


def run_pres_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "presentation_embodiment_surface"
    checks.append(PolicyBatchCheck("pres_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "presentation_embodiment_surface_gate.py"
    checks.append(PolicyBatchCheck("pres_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "presentation_embodiment_surface"
    checks.append(PolicyBatchCheck("pres_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    checks.append(
        PolicyBatchCheck(
            "pres_require_authority_badge_default",
            pres_require_authority_badge(),
            "HG_PRES_REQUIRE_AUTHORITY_BADGE=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "pres_disabled_by_default",
            not pres_enabled(),
            "HG_PRES_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "pres",
        "feature": "PRES",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_pres_closure_checks"]
