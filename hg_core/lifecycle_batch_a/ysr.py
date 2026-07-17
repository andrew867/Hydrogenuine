"""YSR slice closure checks for Batch L3-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.yawn.config import ysr_enabled


def run_ysr_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "yawn"
    checks.append(PolicyBatchCheck("ysr_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "ysr_yawn_soft_reset_gate.py"
    checks.append(PolicyBatchCheck("ysr_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "ysr"
    checks.append(PolicyBatchCheck("ysr_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "yawn_soft_reset" / "YSR_SPEC.md"
    checks.append(PolicyBatchCheck("ysr_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    policy_py = workspace / "hg_runtime" / "yawn" / "policy.py"
    policy_text = policy_py.read_text(encoding="utf-8") if policy_py.is_file() else ""
    checks.append(
        PolicyBatchCheck(
            "ysr_refuses_crr_active",
            "REFUSED_CRR_ACTIVE" in policy_text,
            "policy.py refuses when recovery active",
        )
    )

    config_py = workspace / "hg_runtime" / "yawn" / "config.py"
    config_text = config_py.read_text(encoding="utf-8") if config_py.is_file() else ""
    checks.append(
        PolicyBatchCheck(
            "ysr_escalate_to_crr_default",
            "HG_YSR_ESCALATE_TO_CRR_ON_FAIL" in config_text,
            "escalation config present",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "ysr_disabled_by_default",
            not ysr_enabled(),
            "HG_YSR_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "ysr",
        "feature": "YSR",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_ysr_closure_checks"]
