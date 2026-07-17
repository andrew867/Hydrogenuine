"""EXCITON cluster import fences — no OEA/TER/GPP/UEAK/SRP apply."""

from __future__ import annotations

from pathlib import Path

_BATCH_ROOT = Path(__file__).resolve().parents[1] / "p7_batch_a"
_RUNTIME_ROOT = Path(__file__).resolve().parents[2] / "hg_runtime" / "operator_product_surface"

_FORBIDDEN_IMPORT_TOKENS = (
    "hg_oea",
    "hg_ter",
    "hg_gpp",
    "hg_ueak",
    "hg_srp",
    "import requests",
    "import httpx",
    "subprocess.",
    "PermitAuthority",
    "ExecutionAuthorityKernel",
)


def check_exciton_import_fences() -> tuple[bool, list[str]]:
    failures: list[str] = []
    for root in (_BATCH_ROOT, _RUNTIME_ROOT):
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
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "external_action_taken": False,
        "surface_is_advisory_only": True,
        "polish_is_not_safety": True,
    }


__all__ = ["advisory_only_marker", "check_exciton_import_fences"]
