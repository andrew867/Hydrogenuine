"""P7 Batch B dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.p7_batch_b.embodiment import (
    run_embodiment_audit_slice_checks,
    run_embodiment_closure_checks,
    run_embodiment_proposal_slice_checks,
    run_embodiment_queue_slice_checks,
    run_oea_growth_slice_checks,
)

P7_B_SLICES = ("embodiment", "embodiment_audit", "embodiment_queue", "embodiment_proposal", "oea_growth")
SUPPORTED_SLICES = frozenset({*P7_B_SLICES, "all"})

_SLICE_RUNNERS = {
    "embodiment": run_embodiment_closure_checks,
    "embodiment_audit": run_embodiment_audit_slice_checks,
    "embodiment_queue": run_embodiment_queue_slice_checks,
    "embodiment_proposal": run_embodiment_proposal_slice_checks,
    "oea_growth": run_oea_growth_slice_checks,
}


def run_p7_batch_b_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_p7_batch_b_checks(workspace)
    return _SLICE_RUNNERS[slice](workspace)


def run_all_p7_batch_b_checks(workspace: Path) -> dict[str, Any]:
    slices: dict[str, dict[str, object]] = {}
    critical_failures: list[str] = []
    for name in P7_B_SLICES:
        result = _SLICE_RUNNERS[name](workspace)
        slices[name] = result
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "EMBODIMENT_OEA_GROWTH_AUDIT.md"
    checks: list[PolicyBatchCheck] = [
        PolicyBatchCheck(
            "all_p7b_slices_green",
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
    "P7_B_SLICES",
    "SUPPORTED_SLICES",
    "run_all_p7_batch_b_checks",
    "run_p7_batch_b_checks",
]
