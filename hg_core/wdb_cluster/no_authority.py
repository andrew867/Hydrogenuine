"""WDB cluster import fences — no OEA/TER/GPP/UEAK/SRP apply."""

from __future__ import annotations

from pathlib import Path

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

_PACKAGE_ROOTS = (
    Path(__file__).resolve().parents[1] / "wdb_cluster",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "waste_disposal_boundary",
)


def check_wdb_import_fences() -> tuple[bool, list[str]]:
    failures: list[str] = []
    for root in _PACKAGE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if path.name == "no_authority.py":
                continue
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
        "waste_disposal_is_advisory_only": True,
        "memory_history_mutated": False,
        "permit_minted": False,
        "execution_admitted": False,
        "oea_ter_called": False,
        "deletion_performed": False,
        "tool_removed": False,
        "agent_spawned": False,
    }


__all__ = ["advisory_only_marker", "check_wdb_import_fences"]

