"""MSC slice closure checks for Batch L3-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.msc.config import msc_enabled


def run_msc_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "msc"
    checks.append(PolicyBatchCheck("msc_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "msc_meditation_gate.py"
    checks.append(PolicyBatchCheck("msc_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "msc"
    checks.append(PolicyBatchCheck("msc_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "meditation_cycle" / "MSC_SPEC.md"
    checks.append(PolicyBatchCheck("msc_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    window_py = workspace / "hg_runtime" / "msc" / "window.py"
    window_text = window_py.read_text(encoding="utf-8") if window_py.is_file() else ""
    checks.append(
        PolicyBatchCheck(
            "msc_observes_crr_events",
            "CRR_" in window_text,
            "window.py includes CRR event classification",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "msc_disabled_by_default",
            not msc_enabled(),
            "HG_MSC_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "msc",
        "feature": "MSC",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_msc_closure_checks"]
