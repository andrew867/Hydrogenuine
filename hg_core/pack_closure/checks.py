"""Pack closure dispatcher for Batch CT-B."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.pack_closure.doc_claim import run_doc_claim_closure_checks
from hg_core.pack_closure.rbk_neg1 import run_rbk_neg1_closure_checks
from hg_core.pack_closure.tim_u4 import run_tim_u4_closure_checks
from hg_core.pack_closure.types import PackClosureCheck

SUPPORTED_PACKS = frozenset({"rbk_neg1", "doc_claim_chain", "tim_u4_boundary", "all"})
CT_B_SLICE_PACKS = ("rbk_neg1", "doc_claim_chain", "tim_u4_boundary")


def run_pack_closure_checks(workspace: Path, *, pack: str) -> dict[str, Any]:
    if pack not in SUPPORTED_PACKS:
        return {
            "pack": pack,
            "ok": False,
            "critical_failures": ["unsupported_pack"],
            "checks": [
                PackClosureCheck(
                    "supported_pack",
                    False,
                    f"supported={sorted(SUPPORTED_PACKS)}",
                ).to_payload()
            ],
        }
    if pack == "all":
        return run_all_pack_closure_checks(workspace)
    if pack == "rbk_neg1":
        return run_rbk_neg1_closure_checks(workspace)
    if pack == "doc_claim_chain":
        return run_doc_claim_closure_checks(workspace)
    if pack == "tim_u4_boundary":
        return run_tim_u4_closure_checks(workspace)
    raise AssertionError(f"unhandled pack: {pack}")


def run_all_pack_closure_checks(workspace: Path) -> dict[str, Any]:
    slices = {
        name: run_pack_closure_checks(workspace, pack=name)
        for name in CT_B_SLICE_PACKS
    }
    critical_failures: list[str] = []
    for name, result in slices.items():
        critical_failures.extend(f"{name}:{fid}" for fid in result.get("critical_failures", []))
    return {
        "pack": "all",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "slices": slices,
        "checks": [
            PackClosureCheck(
                f"slice_{name}",
                result["ok"],
                f"critical_failures={result.get('critical_failures', [])}",
            ).to_payload()
            for name, result in slices.items()
        ],
    }


__all__ = [
    "CT_B_SLICE_PACKS",
    "PackClosureCheck",
    "SUPPORTED_PACKS",
    "run_all_pack_closure_checks",
    "run_pack_closure_checks",
]
