"""Runtime Context Batch R2-A dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context_batch_a.bcp import run_bcp_closure_checks
from hg_core.runtime_context_batch_a.pres import run_pres_closure_checks
from hg_core.runtime_context_batch_a.res import run_res_closure_checks

R2_A_SLICES = ("bcp", "pres", "res")
SUPPORTED_SLICES = frozenset({*R2_A_SLICES, "all"})


def run_runtime_context_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
    if slice not in SUPPORTED_SLICES:
        return {
            "slice": slice,
            "ok": False,
            "critical_failures": ["unsupported_slice"],
            "checks": [
                PolicyBatchCheck(
                    "supported_slice",
                    False,
                    f"supported={sorted(SUPPORTED_SLICES)}",
                ).to_payload()
            ],
        }
    if slice == "all":
        return run_all_runtime_context_batch_a_checks(workspace)
    if slice == "bcp":
        return run_bcp_closure_checks(workspace)
    if slice == "pres":
        return run_pres_closure_checks(workspace)
    if slice == "res":
        return run_res_closure_checks(workspace)
    raise AssertionError(f"unhandled slice: {slice}")


def run_all_runtime_context_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices = {name: run_runtime_context_batch_a_checks(workspace, slice=name) for name in R2_A_SLICES}
    critical_failures: list[str] = []
    for name, result in slices.items():
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "RUNTIME_CONTEXT_BATCH_A_AUDIT.md"
    checks: list[PolicyBatchCheck] = [
        PolicyBatchCheck(
            f"slice_{name}",
            result["ok"],
            f"critical_failures={result.get('critical_failures', [])}",
        )
        for name, result in slices.items()
    ]
    checks.append(
        PolicyBatchCheck(
            "batch_audit_report_present",
            report.is_file(),
            str(report.relative_to(workspace)).replace("\\", "/"),
        )
    )

    for check in checks:
        if check.critical and not check.ok:
            critical_failures.append(check.check_id)

    return {
        "slice": "all",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "slices": slices,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "R2_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_runtime_context_batch_a_checks",
    "run_runtime_context_batch_a_checks",
]
