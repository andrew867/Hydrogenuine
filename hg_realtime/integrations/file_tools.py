"""L10 file tool: file.parse(path) with idempotency per path. Phase 7."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict

from .tool_router import ToolCall


def _get_workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _get(call: ToolCall, key: str, default: Any = None) -> Any:
    return call.args.get(key, default)


def _safe_path(path_arg: str, workspace: Path | None) -> Path | None:
    """Resolve path; if relative, under workspace. Reject path traversal and paths outside workspace."""
    if not path_arg or not isinstance(path_arg, str):
        return None
    if workspace is None:
        return None
    p = Path(path_arg)
    if p.is_absolute():
        resolved = p
    else:
        resolved = (workspace / path_arg).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError:
        return None
    return resolved


def handler_file_parse(call: ToolCall) -> Dict[str, Any]:
    """Parse file at path; return content preview and size. Idempotency per path."""
    path_arg = _get(call, "path")
    if not path_arg:
        return {"ok": False, "error": "path is required", "action": "file.parse"}
    workspace = _get(call, "workspace")
    if workspace is not None:
        workspace = Path(workspace) if isinstance(workspace, str) else workspace
    else:
        workspace = _get_workspace_root()
    path = _safe_path(str(path_arg), workspace)
    if path is None:
        return {"ok": False, "error": "path invalid or outside workspace", "action": "file.parse"}
    if not path.exists():
        return {"ok": False, "error": f"file not found: {path}", "action": "file.parse"}
    if not path.is_file():
        return {"ok": False, "error": f"not a file: {path}", "action": "file.parse"}
    try:
        raw = path.read_bytes()
        size = len(raw)
        # Preview: decode as utf-8, first 8k chars
        try:
            text = raw.decode("utf-8", errors="replace")
            preview = text[:8192] if len(text) > 8192 else text
        except Exception:
            preview = ""
        return {
            "ok": True,
            "data": {
                "path": str(path),
                "size": size,
                "content_preview": preview,
                "preview_truncated": size > 8192,
            },
            "action": "file.parse",
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "file.parse"}


def idempotency_key_for_file_parse(path: str) -> str:
    """Stable idempotency key per path (min 8 chars)."""
    h = hashlib.sha256(path.encode("utf-8", errors="replace")).hexdigest()
    return f"file-parse-{h[:24]}"
