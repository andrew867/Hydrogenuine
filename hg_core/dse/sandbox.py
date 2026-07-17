"""DSE sandbox path validator — refuse writes outside configured roots."""

from __future__ import annotations

from pathlib import Path

from hg_core.dse.config import dse_sandbox_root
from hg_core.dse.errors import REFUSED_UNAUTHORIZED_PATH
from hg_core.secrets.redact import contains_leak


def resolve_sandbox_path(target: str | Path, *, allowed_root: Path) -> tuple[Path | None, str]:
    """Resolve target under allowed_root; refuse traversal and secrets."""
    if contains_leak({"target": str(target)}):
        return None, REFUSED_UNAUTHORIZED_PATH

    root = allowed_root.resolve()
    try:
        candidate = (root / str(target)).resolve()
    except (OSError, ValueError):
        return None, REFUSED_UNAUTHORIZED_PATH

    if not str(candidate).startswith(str(root)):
        return None, REFUSED_UNAUTHORIZED_PATH

    return candidate, ""


def validate_path_in_sandbox(target: str | Path, *, allowed_root: Path | None = None) -> tuple[bool, str, Path | None]:
    root = allowed_root or dse_sandbox_root()
    resolved, reason = resolve_sandbox_path(target, allowed_root=root)
    if resolved is None:
        return False, reason or REFUSED_UNAUTHORIZED_PATH, None
    return True, "", resolved


def deterministic_filename(prefix: str, request_id: str, *, suffix: str = ".json") -> str:
    safe_id = "".join(c if c.isalnum() or c in "-_" else "-" for c in request_id)
    return f"{prefix}-{safe_id[:32]}{suffix}"


__all__ = ["deterministic_filename", "resolve_sandbox_path", "validate_path_in_sandbox"]
