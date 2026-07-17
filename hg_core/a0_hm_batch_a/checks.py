"""A0-HM Batch A0-HM dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.a0_hm_batch_a.a0_hm import (
    run_a0_hm_closure_checks,
    run_a0_hm_receipt_slice_checks,
    run_a0_hm_reception_slice_checks,
    run_a0_hm_route_slice_checks,
    run_a0_hm_snapshot_slice_checks,
)
from hg_core.policy_batch_a.types import PolicyBatchCheck

A0_HM_A_SLICES = ("a0_hm", "a0_hm_reception", "a0_hm_route", "a0_hm_receipt", "a0_hm_snapshot")
SUPPORTED_SLICES = frozenset({*A0_HM_A_SLICES, "all"})

_SLICE_RUNNERS = {
    "a0_hm": run_a0_hm_closure_checks,
    "a0_hm_reception": run_a0_hm_reception_slice_checks,
    "a0_hm_route": run_a0_hm_route_slice_checks,
    "a0_hm_receipt": run_a0_hm_receipt_slice_checks,
    "a0_hm_snapshot": run_a0_hm_snapshot_slice_checks,
}


def run_a0_hm_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_a0_hm_batch_a_checks(workspace)
    return _SLICE_RUNNERS[slice](workspace)


def run_all_a0_hm_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices: dict[str, dict[str, object]] = {}
    critical_failures: list[str] = []
    for name in A0_HM_A_SLICES:
        result = _SLICE_RUNNERS[name](workspace)
        slices[name] = result
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "A0_HM_FIRST_SLICE_AUDIT.md"
    checks: list[PolicyBatchCheck] = [
        PolicyBatchCheck(
            "all_a0_hm_slices_green",
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
    "A0_HM_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_a0_hm_batch_a_checks",
    "run_a0_hm_batch_a_checks",
]
