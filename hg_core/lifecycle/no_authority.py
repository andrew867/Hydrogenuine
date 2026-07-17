"""Lifecycle import fences — no OEA/TER/GPP/UEAK/SRP apply."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_IMPORT_TOKENS = (
    "hg_oea",
    "hg_ter",
    "hg_gpp",
    "hg_ueak",
    "PermitAuthority",
    "ExecutionAuthorityKernel",
    "import requests",
    "import httpx",
    "subprocess.",
)

_PACKAGE_ROOTS = (
    Path(__file__).resolve().parents[1] / "lifecycle_batch_a",
    Path(__file__).resolve().parents[1] / "lifecycle_batch_b",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "coordinated_rest_recovery",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "continuity_boundary",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "emergence",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "mortality_memory_offering",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "msc",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "yawn",
)


def check_lifecycle_import_fences() -> tuple[bool, list[str]]:
    failures: list[str] = []
    for root in _PACKAGE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue
                for token in _FORBIDDEN_IMPORT_TOKENS:
                    if token in line:
                        rel = path.as_posix().split("workspace/", 1)[-1]
                        failures.append(f"{rel}: forbidden import {token!r}")
    return not failures, failures


def advisory_only_marker() -> dict[str, bool]:
    return {"advisory_only": True, "permission_granted": False, "authority_created": False}


__all__ = ["advisory_only_marker", "check_lifecycle_import_fences"]
