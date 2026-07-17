"""Pack 11 TIM-U4 boundary closure — stale authority proven; full TIM honestly deferred."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.pack_closure.proof_bundles import find_latest_green_gate_bundle
from hg_core.pack_closure.types import PackClosureCheck


def run_tim_u4_closure_checks(workspace: Path) -> dict[str, Any]:
    checks: list[PackClosureCheck] = []

    gate_path = workspace / "scripts" / "evals" / "time_semantics_gate.py"
    checks.append(
        PackClosureCheck(
            "time_semantics_gate_present",
            gate_path.is_file(),
            str(gate_path.relative_to(workspace)).replace("\\", "/"),
        )
    )

    test_path = workspace / "tests" / "tim_u4" / "test_time_semantics_u4.py"
    checks.append(
        PackClosureCheck(
            "tim_u4_tests_present",
            test_path.is_file(),
            str(test_path.relative_to(workspace)).replace("\\", "/"),
        )
    )

    status_path = workspace / "docs" / "reports" / "phases" / "CT-11-TIM-U4-STATUS.md"
    status_text = status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
    checks.append(
        PackClosureCheck(
            "tim_u4_status_report_present",
            status_path.is_file(),
            str(status_path.relative_to(workspace)).replace("\\", "/"),
        )
    )

    honest_deferral = status_path.is_file() and any(
        token in status_text.lower()
        for token in ("not_proven", "deferred", "honesty")
    )
    checks.append(
        PackClosureCheck(
            "full_tim_honestly_deferred_in_status",
            honest_deferral,
            "CT-11-TIM-U4-STATUS documents full-pack deferral",
        )
    )

    inventory = workspace / "docs" / "reports" / "phases" / "CT_DEFERRED_ITEM_INVENTORY.md"
    inv_text = inventory.read_text(encoding="utf-8") if inventory.is_file() else ""
    d08_deferred = "D-08" in inv_text and "POST_CT" in inv_text
    checks.append(
        PackClosureCheck(
            "full_tim_deferred_in_inventory",
            d08_deferred,
            "D-08 POST_CT backburner for TIM-U6/U7/E1",
        )
    )

    admission_path = workspace / "hg_core" / "admission" / "controller.py"
    admission_text = admission_path.read_text(encoding="utf-8") if admission_path.is_file() else ""
    stale_refusal = "admission.refused.stale_approval" in admission_text
    checks.append(
        PackClosureCheck(
            "stale_approval_refusal_preserved",
            stale_refusal,
            "admission controller refuses stale approval",
        )
    )

    expiry_path = workspace / "hg_core" / "time" / "expiry.py"
    expiry_text = expiry_path.read_text(encoding="utf-8") if expiry_path.is_file() else ""
    boundary_semantics = "STALE_APPROVAL" in expiry_text and "is_expired" in expiry_text
    checks.append(
        PackClosureCheck(
            "expiry_boundary_semantics_present",
            boundary_semantics,
            "expiry module defines boundary refusal",
        )
    )

    bundle = find_latest_green_gate_bundle(workspace, "pack11")
    checks.append(
        PackClosureCheck(
            "pack11_tim_u4_proof_bundle_green",
            bundle is not None,
            str(bundle.relative_to(workspace)).replace("\\", "/") if bundle else "no green pack11 bundle",
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "pack": "tim_u4_boundary",
        "packs": ("CT-11",),
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "full_pack_tim": {
            "status": "deferred_post_ct",
            "slice": "TIM-U4",
            "inventory_ref": "D-08",
        },
    }


__all__ = ["run_tim_u4_closure_checks"]
