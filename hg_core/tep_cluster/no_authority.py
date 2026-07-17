"""TEP cluster import fences — no OEA/TER/GPP mint/UEAK admission/SRP apply."""

from __future__ import annotations

from pathlib import Path

_RUNTIME_ROOT = Path(__file__).resolve().parents[2] / "hg_runtime" / "translation_envelope_protocol"

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
    "mint_permit",
    "admit_execution",
)


def check_tep_import_fences() -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not _RUNTIME_ROOT.is_dir():
        failures.append("hg_runtime/translation_envelope_protocol missing")
        return False, failures
    for path in sorted(_RUNTIME_ROOT.rglob("*.py")):
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
        "translation_is_not_authority": True,
    }


__all__ = ["advisory_only_marker", "check_tep_import_fences"]
