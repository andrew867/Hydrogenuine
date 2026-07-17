"""OEA-TER-LIVE import fences — no live external surfaces, GPP mint, or UEAK admission."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_IMPORT_TOKENS = (
    "import requests",
    "import httpx",
    "subprocess.",
    "PermitAuthority",
    "ExecutionAuthorityKernel",
    "hg_oea.bounded_executor",
    "OEABoundedExecutor",
)

_PACKAGE_ROOTS = (
    Path(__file__).resolve().parents[2] / "hg_runtime" / "live_oea_ter_bridge",
)


def check_oea_ter_import_fences() -> tuple[bool, list[str]]:
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
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "evidence_admissible": False,
        "oea_ter_dispatch_is_advisory_only": True,
        "live_action_performed": False,
        "oea_ter_called": False,
    }


__all__ = ["advisory_only_marker", "check_oea_ter_import_fences"]
