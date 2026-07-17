"""Developmental Batch D4-B dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.developmental_batch_b.iil import run_iil_closure_checks
from hg_core.developmental_batch_b.rgl import run_rgl_closure_checks
from hg_core.developmental_batch_b.scl import run_scl_closure_checks
from hg_core.policy_batch_a.types import PolicyBatchCheck

D4_B_SLICES = ("rgl", "scl", "iil")
SUPPORTED_SLICES = frozenset({*D4_B_SLICES, "all"})


def run_developmental_batch_b_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_developmental_batch_b_checks(workspace)
    if slice == "rgl":
        return run_rgl_closure_checks(workspace)
    if slice == "scl":
        return run_scl_closure_checks(workspace)
    if slice == "iil":
        return run_iil_closure_checks(workspace)
    raise AssertionError(f"unhandled slice: {slice}")


def run_all_developmental_batch_b_checks(workspace: Path) -> dict[str, Any]:
    slices = {name: run_developmental_batch_b_checks(workspace, slice=name) for name in D4_B_SLICES}
    critical_failures: list[str] = []
    for name, result in slices.items():
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "L4_L6_DEVELOPMENTAL_AUDIT.md"
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
    "D4_B_SLICES",
    "SUPPORTED_SLICES",
    "run_all_developmental_batch_b_checks",
    "run_developmental_batch_b_checks",
]
