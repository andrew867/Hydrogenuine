"""RES slice closure checks for Batch R2-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import res_enabled, res_offline_only


def run_res_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "research_evidence_acquisition"
    checks.append(PolicyBatchCheck("res_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "research_evidence_acquisition_gate.py"
    checks.append(PolicyBatchCheck("res_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "research_evidence_acquisition"
    checks.append(PolicyBatchCheck("res_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    checks.append(
        PolicyBatchCheck(
            "res_offline_only_default",
            res_offline_only(),
            "HG_RES_OFFLINE_ONLY=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "res_disabled_by_default",
            not res_enabled(),
            "HG_RES_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "res",
        "feature": "RES",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_res_closure_checks"]
