"""Phase 38 deterministic unified-diff parser.

Parses unified-diff text into a structured ``parsed_diff_v1`` without applying
anything. It only reads the patch text; it never touches the working tree.
"""

from __future__ import annotations

import re
from typing import Any

from hg_runtime.patch_candidate_sandbox.schemas import (
    DIFF_FILE_CHANGE_SCHEMA,
    PARSED_DIFF_SCHEMA,
)

_DIFF_GIT_RE = re.compile(r"^diff --git a/(?P<a>.+?) b/(?P<b>.+?)\s*$")
_MINUS_RE = re.compile(r"^--- (?:a/)?(?P<path>.+?)\s*$")
_PLUS_RE = re.compile(r"^\+\+\+ (?:b/)?(?P<path>.+?)\s*$")


def _strip_prefix(path: str) -> str:
    path = path.strip()
    if path in ("/dev/null", ""):
        return path
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            return path[len(prefix) :]
    return path


def parse_unified_diff(diff_text: str) -> dict[str, Any]:
    """Parse unified-diff text into ``parsed_diff_v1`` (read-only)."""
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def _flush() -> None:
        nonlocal current
        if current is not None:
            files.append(current)
            current = None

    for raw in diff_text.splitlines():
        git_match = _DIFF_GIT_RE.match(raw)
        if git_match:
            _flush()
            path = _strip_prefix(git_match.group("b")) or _strip_prefix(git_match.group("a"))
            current = _new_file(path)
            continue
        if raw.startswith("--- "):
            minus = _MINUS_RE.match(raw)
            if minus and current is None:
                current = _new_file(_strip_prefix(minus.group("path")))
            continue
        if raw.startswith("+++ "):
            plus = _PLUS_RE.match(raw)
            if plus and current is not None:
                new_path = _strip_prefix(plus.group("path"))
                if new_path and new_path != "/dev/null":
                    current["path"] = new_path
            continue
        if current is None:
            continue
        if raw.startswith("@@"):
            current["hunks"] += 1
        elif raw.startswith("+") and not raw.startswith("+++"):
            current["added_lines"] += 1
            current["added_content"].append(raw[1:])
        elif raw.startswith("-") and not raw.startswith("---"):
            current["removed_lines"] += 1
    _flush()

    return {
        "schema": PARSED_DIFF_SCHEMA,
        "file_count": len(files),
        "files": files,
        "parseable": bool(files),
        "changed_paths": [f["path"] for f in files],
    }


def _new_file(path: str) -> dict[str, Any]:
    return {
        "schema": DIFF_FILE_CHANGE_SCHEMA,
        "path": path,
        "added_lines": 0,
        "removed_lines": 0,
        "hunks": 0,
        "added_content": [],
    }


__all__ = ["parse_unified_diff"]
