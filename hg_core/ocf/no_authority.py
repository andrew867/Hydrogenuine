"""OCF no-authority markers and import fences."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_IMPORT_TOKENS = (
    "hg_oea",
    "hg_ter",
    "PermitAuthority",
    "ExecutionAuthorityKernel",
    "durable_side_effect",
    "live_memory_mutation",
    "grant_authority_live",
    "live_srp_apply",
    "live_publication_external",
    "live_reproduction_spawn",
    "live_autonomous_loop",
)

_PACKAGE_ROOTS = (
    Path(__file__).resolve().parents[2] / "hg_runtime" / "organ_control_fields",
)


def check_ocf_import_fences() -> tuple[bool, list[str]]:
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
        "durable_write_performed": False,
        "live_action_performed": False,
        "ocf_is_advisory_only": True,
    }


__all__ = ["advisory_only_marker", "check_ocf_import_fences"]
