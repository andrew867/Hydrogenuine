"""Policy-safety import fences — no OEA/TER/GPP/UEAK/SRP apply."""

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
    Path(__file__).resolve().parents[1] / "policy_batch_a",
    Path(__file__).resolve().parents[1] / "policy_batch_b",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "synthetic_content_provenance",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "ai_interaction_disclosure",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "democratic_misinformation_integrity",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "frontier_capability_evaluation",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "vulnerable_subject_protection",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "compromised_disconnected_operation",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "certification_evidence_pack",
)


def check_policy_import_fences() -> tuple[bool, list[str]]:
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
    """Explicit marker that policy outputs are not permission."""
    return {"advisory_only": True, "permission_granted": False, "authority_created": False}


__all__ = ["advisory_only_marker", "check_policy_import_fences"]
