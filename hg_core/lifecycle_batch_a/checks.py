"""Lifecycle Batch L3-A dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.lifecycle_batch_a.crr import run_crr_closure_checks
from hg_core.lifecycle_batch_a.els import run_els_closure_checks
from hg_core.lifecycle_batch_a.msc import run_msc_closure_checks
from hg_core.lifecycle_batch_a.ysr import run_ysr_closure_checks
from hg_core.policy_batch_a.types import PolicyBatchCheck

L3_A_SLICES = ("els", "msc", "ysr", "crr")
SUPPORTED_SLICES = frozenset({*L3_A_SLICES, "all"})


def run_lifecycle_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_lifecycle_batch_a_checks(workspace)
    if slice == "els":
        return run_els_closure_checks(workspace)
    if slice == "msc":
        return run_msc_closure_checks(workspace)
    if slice == "ysr":
        return run_ysr_closure_checks(workspace)
    if slice == "crr":
        return run_crr_closure_checks(workspace)
    raise AssertionError(f"unhandled slice: {slice}")


def run_all_lifecycle_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices = {name: run_lifecycle_batch_a_checks(workspace, slice=name) for name in L3_A_SLICES}
    critical_failures: list[str] = []
    for name, result in slices.items():
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "LIFECYCLE_BATCH_A_AUDIT.md"
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
    "L3_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_lifecycle_batch_a_checks",
    "run_lifecycle_batch_a_checks",
]
