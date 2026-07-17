"""EOG cluster import fences — no OEA/TER/GPP/UEAK/SRP apply."""

from __future__ import annotations

from pathlib import Path

_BATCH_ROOT = Path(__file__).resolve().parents[1] / "p7_batch_b"
_RUNTIME_ROOT = Path(__file__).resolve().parents[2] / "hg_runtime" / "embodiment_oea_growth"

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


def check_eog_import_fences() -> tuple[bool, list[str]]:
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
        "embodiment_is_not_consent": True,
        "reach_is_not_actuation_permission": True,
    }


__all__ = ["advisory_only_marker", "check_eog_import_fences"]
