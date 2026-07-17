"""Policy Batch P1-B dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.policy_batch_b.cdo import run_cdo_closure_checks
from hg_core.policy_batch_b.crt import run_crt_closure_checks
from hg_core.policy_batch_b.fce import run_fce_closure_checks
from hg_core.policy_batch_b.vsp import run_vsp_closure_checks

P1_B_SLICES = ("fce", "vsp", "cdo", "crt")
SUPPORTED_SLICES = frozenset({*P1_B_SLICES, "all"})


def run_policy_batch_b_checks(workspace: Path, *, slice: str) -> dict[str, Any]:
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
        return run_all_policy_batch_b_checks(workspace)
    if slice == "fce":
        return run_fce_closure_checks(workspace)
    if slice == "vsp":
        return run_vsp_closure_checks(workspace)
    if slice == "cdo":
        return run_cdo_closure_checks(workspace)
    if slice == "crt":
        return run_crt_closure_checks(workspace)
    raise AssertionError(f"unhandled slice: {slice}")


def run_all_policy_batch_b_checks(workspace: Path) -> dict[str, Any]:
    slices = {name: run_policy_batch_b_checks(workspace, slice=name) for name in P1_B_SLICES}
    critical_failures: list[str] = []
    for name, result in slices.items():
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))

    report = workspace / "docs" / "reports" / "phases" / "POLICY_BATCH_B_AUDIT.md"
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
    "P1_B_SLICES",
    "SUPPORTED_SLICES",
    "run_all_policy_batch_b_checks",
    "run_policy_batch_b_checks",
]
