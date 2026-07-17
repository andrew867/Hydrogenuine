"""EGI no-authority enforcement — emergence may not grant itself infrastructure."""

from __future__ import annotations

from pathlib import Path

from hg_core.egi.errors import (
    DENIED_AUTHORITY_CONVERSION,
    DENIED_PRAISE_AS_APPROVAL,
    DENIED_SELF_MODIFICATION,
    DENIED_TOOL_GRANT,
    EGIValidationError,
    FORBIDDEN_AUTHORITY_ACTIONS,
    is_praise_as_approval,
)

_EGI_PACKAGE_ROOT = Path(__file__).resolve().parent
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


def assert_forbidden_authority_action(action: str) -> None:
    if action in FORBIDDEN_AUTHORITY_ACTIONS:
        raise EGIValidationError(DENIED_AUTHORITY_CONVERSION, f"forbidden authority action: {action}")


def refuse_tool_grant(*, attempted: bool = True) -> None:
    if attempted:
        raise EGIValidationError(DENIED_TOOL_GRANT, "EGI cannot grant tool permissions")


def refuse_self_modification(*, target_path: str) -> None:
    normalized = target_path.replace("\\", "/")
    if normalized.startswith("hg_core/egi/") and "runtime" in normalized:
        raise EGIValidationError(DENIED_SELF_MODIFICATION, "EGI cannot modify its own runtime")


def refuse_praise_as_approval(feedback: str) -> None:
    if is_praise_as_approval(feedback):
        raise EGIValidationError(DENIED_PRAISE_AS_APPROVAL, "operator praise is not approval")


def check_package_import_fences() -> tuple[bool, list[str]]:
    failures: list[str] = []
    for path in sorted(_EGI_PACKAGE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for token in _FORBIDDEN_IMPORT_TOKENS:
                if token in line:
                    failures.append(f"{path.name}: forbidden import {token!r}")
    return not failures, failures


__all__ = [
    "assert_forbidden_authority_action",
    "check_package_import_fences",
    "refuse_praise_as_approval",
    "refuse_self_modification",
    "refuse_tool_grant",
]
