"""CT-C acceptance slice dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.ct_acceptance.final_audit import run_ct_full_final_audit_checks
from hg_core.ct_acceptance.milestone import run_ct_v1_milestone_checks
from hg_core.ct_acceptance.reconcile import AcceptanceCheck, run_ct_acceptance_reconcile

CT_C_SLICES = ("reconcile", "milestone", "full", "all")
SUPPORTED_SLICES = frozenset(CT_C_SLICES)


def run_ct_acceptance_checks(
    workspace: Path,
    *,
    slice: str,
    fresh_ct_v1_bundle: Path | None = None,
) -> dict[str, Any]:
    if slice not in SUPPORTED_SLICES:
        return {
            "slice": slice,
            "ok": False,
            "critical_failures": ["unsupported_slice"],
            "checks": [
                AcceptanceCheck(
                    "supported_slice",
                    False,
                    f"supported={sorted(SUPPORTED_SLICES)}",
                ).to_payload()
            ],
        }
    if slice == "reconcile":
        result = run_ct_acceptance_reconcile(workspace)
        return {**result, "slice": "reconcile"}
    if slice == "milestone":
        return run_ct_v1_milestone_checks(workspace, fresh_bundle=fresh_ct_v1_bundle)
    if slice == "full":
        return run_ct_full_final_audit_checks(workspace, fresh_ct_v1_bundle=fresh_ct_v1_bundle)
    if slice == "all":
        return run_all_ct_acceptance_checks(workspace, fresh_ct_v1_bundle=fresh_ct_v1_bundle)
    raise AssertionError(f"unhandled slice: {slice}")


def run_all_ct_acceptance_checks(
    workspace: Path,
    *,
    fresh_ct_v1_bundle: Path | None = None,
) -> dict[str, Any]:
    reconcile = run_ct_acceptance_reconcile(workspace)
    milestone = run_ct_v1_milestone_checks(workspace, fresh_bundle=fresh_ct_v1_bundle)
    full = run_ct_full_final_audit_checks(workspace, fresh_ct_v1_bundle=fresh_ct_v1_bundle)
    critical_failures: list[str] = []
    for name, result in (("reconcile", reconcile), ("milestone", milestone), ("full", full)):
        if not result["ok"]:
            critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))
    return {
        "slice": "all",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "slices": {
            "reconcile": reconcile,
            "milestone": milestone,
            "full": full,
        },
        "checks": [
            AcceptanceCheck(
                f"slice_{name}",
                result["ok"],
                f"critical_failures={result.get('critical_failures', [])}",
            ).to_payload()
            for name, result in (("reconcile", reconcile), ("milestone", milestone), ("full", full))
        ],
    }


__all__ = [
    "CT_C_SLICES",
    "SUPPORTED_SLICES",
    "run_all_ct_acceptance_checks",
    "run_ct_acceptance_checks",
]
