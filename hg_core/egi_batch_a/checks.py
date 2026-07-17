"""EGI Batch A dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.egi_batch_a.egi import (
    run_egi_closure_checks,
    run_egi_packet_slice_checks,
    run_egi_queue_slice_checks,
)
from hg_core.policy_batch_a.types import PolicyBatchCheck

EGI_A_SLICES = ("egi", "egi_packet", "egi_queue")
SUPPORTED_SLICES = frozenset({*EGI_A_SLICES, "all"})

_SLICE_RUNNERS = {
    "egi": run_egi_closure_checks,
    "egi_packet": run_egi_packet_slice_checks,
    "egi_queue": run_egi_queue_slice_checks,
}


def run_egi_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_egi_batch_a_checks(workspace)
    return _SLICE_RUNNERS[slice](workspace)


def run_all_egi_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices: dict[str, dict[str, object]] = {}
    critical_failures: list[str] = []
    for name in EGI_A_SLICES:
        result = _SLICE_RUNNERS[name](workspace)
        slices[name] = result
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "EGI_FIRST_SLICE_AUDIT.md"
    checks: list[PolicyBatchCheck] = [
        PolicyBatchCheck(
            "all_egi_slices_green",
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
    "EGI_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_egi_batch_a_checks",
    "run_egi_batch_a_checks",
]
