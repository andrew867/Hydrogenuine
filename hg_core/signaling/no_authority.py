"""Signaling import fences — no OEA/TER/GPP/UEAK/SRP apply."""

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
    Path(__file__).resolve().parents[1] / "signaling_batch_a",
    Path(__file__).resolve().parents[1] / "signaling_batch_b",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "semantic_birdsong",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "distributed_attention_casting",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "ambient_proximity_cues",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "self_maximization_loop",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "karmic_action_residue",
    Path(__file__).resolve().parents[1] / "signaling_batch_c",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "neglect_detection",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "silence_discipline",
    Path(__file__).resolve().parents[2] / "hg_runtime" / "affective_field_consensus",
)


def check_signaling_import_fences() -> tuple[bool, list[str]]:
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


__all__ = ["advisory_only_marker", "check_signaling_import_fences"]
