"""ARB Batch A dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.arb_batch_a.arb import (
    run_arb_audit_slice_checks,
    run_arb_closure_checks,
    run_arb_integration_slice_checks,
    run_arb_proposal_slice_checks,
)
from hg_core.policy_batch_a.types import PolicyBatchCheck

ARB_A_SLICES = ("arb", "arb_audit", "arb_integration", "arb_proposal")
SUPPORTED_SLICES = frozenset({*ARB_A_SLICES, "all"})

_SLICE_RUNNERS = {
    "arb": run_arb_closure_checks,
    "arb_audit": run_arb_audit_slice_checks,
    "arb_integration": run_arb_integration_slice_checks,
    "arb_proposal": run_arb_proposal_slice_checks,
}


def run_arb_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_arb_batch_a_checks(workspace)
    return _SLICE_RUNNERS[slice](workspace)


def run_all_arb_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices: dict[str, dict[str, object]] = {}
    critical_failures: list[str] = []
    for name in ARB_A_SLICES:
        result = _SLICE_RUNNERS[name](workspace)
        slices[name] = result
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "ARB_FIRST_SLICE_AUDIT.md"
    completion = workspace / "docs" / "reports" / "phases" / "ARB_FULL_SCOPED_COMPLETION_AUDIT.md"
    checks: list[PolicyBatchCheck] = [
        PolicyBatchCheck(
            "all_arb_slices_green",
            not critical_failures,
            f"critical_failures={critical_failures}",
        ),
        PolicyBatchCheck(
            "batch_audit_report_present",
            report.is_file(),
            str(report.relative_to(workspace)).replace("\\", "/"),
        ),
        PolicyBatchCheck(
            "full_scoped_completion_audit_present",
            completion.is_file(),
            str(completion.relative_to(workspace)).replace("\\", "/"),
        ),
    ]
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
    "ARB_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_arb_batch_a_checks",
    "run_arb_batch_a_checks",
]
