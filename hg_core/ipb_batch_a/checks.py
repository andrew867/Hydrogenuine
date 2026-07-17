"""IPB Batch A dispatcher — full slice scope."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.ipb_batch_a.ipb import (
    run_ipb_advisory_slice_checks,
    run_ipb_audit_slice_checks,
    run_ipb_closure_checks,
    run_ipb_extras_slice_checks,
    run_ipb_policy_slice_checks,
)
from hg_core.policy_batch_a.types import PolicyBatchCheck

IPB_A_SLICES = ("ipb", "ipb_audit", "ipb_advisory", "ipb_policy", "ipb_extras")
SUPPORTED_SLICES = frozenset({*IPB_A_SLICES, "all"})

_SLICE_RUNNERS = {
    "ipb": run_ipb_closure_checks,
    "ipb_audit": run_ipb_audit_slice_checks,
    "ipb_advisory": run_ipb_advisory_slice_checks,
    "ipb_policy": run_ipb_policy_slice_checks,
    "ipb_extras": run_ipb_extras_slice_checks,
}


def run_ipb_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_ipb_batch_a_checks(workspace)
    return _SLICE_RUNNERS[slice](workspace)


def run_all_ipb_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices: dict[str, dict[str, object]] = {}
    critical_failures: list[str] = []
    for name in IPB_A_SLICES:
        result = _SLICE_RUNNERS[name](workspace)
        slices[name] = result
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "IPB_FULL_SCOPED_COMPLETION_AUDIT.md"
    checks: list[PolicyBatchCheck] = [
        PolicyBatchCheck(
            "all_ipb_slices_green",
            not critical_failures,
            f"critical_failures={critical_failures}",
        ),
        PolicyBatchCheck(
            "batch_audit_report_present",
            report.is_file(),
            str(report.relative_to(workspace)).replace("\\", "/"),
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
    "IPB_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_ipb_batch_a_checks",
    "run_ipb_batch_a_checks",
]
