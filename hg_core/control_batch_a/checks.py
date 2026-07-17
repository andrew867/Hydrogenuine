"""Control Batch C6-A dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.control_batch_a.gcb import run_gcb_closure_checks
from hg_core.control_batch_a.mis import run_mis_closure_checks
from hg_core.control_batch_a.pab import run_pab_closure_checks
from hg_core.control_batch_a.rpb import run_rpb_closure_checks
from hg_core.control_batch_a.rsc import run_rsc_closure_checks
from hg_core.control_batch_a.trb import run_trb_closure_checks
from hg_core.policy_batch_a.types import PolicyBatchCheck

C6_A_SLICES = ("rsc", "pab", "mis", "gcb", "trb", "rpb")
SUPPORTED_SLICES = frozenset({*C6_A_SLICES, "all"})


def run_control_batch_a_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_control_batch_a_checks(workspace)
    dispatch = {
        "rsc": run_rsc_closure_checks,
        "pab": run_pab_closure_checks,
        "mis": run_mis_closure_checks,
        "gcb": run_gcb_closure_checks,
        "trb": run_trb_closure_checks,
        "rpb": run_rpb_closure_checks,
    }
    return dispatch[slice](workspace)


def run_all_control_batch_a_checks(workspace: Path) -> dict[str, Any]:
    slices = {name: run_control_batch_a_checks(workspace, slice=name) for name in C6_A_SLICES}
    critical_failures: list[str] = []
    for name, result in slices.items():
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "CONTROL_TRUST_SCARCITY_MISSION_AUDIT.md"
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
    "C6_A_SLICES",
    "SUPPORTED_SLICES",
    "run_all_control_batch_a_checks",
    "run_control_batch_a_checks",
]
