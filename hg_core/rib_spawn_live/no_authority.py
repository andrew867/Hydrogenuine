"""RIB-SPAWN-LIVE import fences — no OEA/TER/GPP mint/UEAK/SRP apply/subprocess spawn."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_IMPORT_TOKENS = (
    "hg_oea",
    "hg_ter",
    "import requests",
    "import httpx",
    "subprocess.",
    "multiprocessing.",
    "os.fork",
    "PermitAuthority",
    "ExecutionAuthorityKernel",
)

_PACKAGE_ROOTS = (
    Path(__file__).resolve().parents[2] / "hg_runtime" / "live_reproduction_spawn",
)


def check_rib_spawn_import_fences() -> tuple[bool, list[str]]:
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
        "spawn_plan_is_advisory_only": True,
        "live_spawn_performed": False,
        "child_inherits_authority": False,
        "live_action_performed": False,
    }


__all__ = ["advisory_only_marker", "check_rib_spawn_import_fences"]
