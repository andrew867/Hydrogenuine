"""Shared file I/O helpers with safe defaults and optional auto-create behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_text(
    path: Path,
    *,
    default: str = "",
    create_if_missing: bool = False,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> str:
    if path.exists():
        return path.read_text(encoding=encoding, errors=errors)
    if create_if_missing:
        ensure_parent(path)
        path.write_text(default, encoding=encoding)
    return default


def write_text(
    path: Path,
    content: str,
    *,
    encoding: str = "utf-8",
    append: bool = False,
) -> None:
    ensure_parent(path)
    mode = "a" if append else "w"
    with open(path, mode, encoding=encoding) as f:
        f.write(content)


def read_json(
    path: Path,
    *,
    default: Any = None,
    create_if_missing: bool = False,
    encoding: str = "utf-8",
) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding=encoding))
        except (json.JSONDecodeError, OSError):
            return default
    if create_if_missing:
        write_json(path, default if default is not None else {}, encoding=encoding)
    return default


def write_json(
    path: Path,
    data: Any,
    *,
    encoding: str = "utf-8",
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    ensure_parent(path)
    with open(path, "w", encoding=encoding) as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        f.write("\n")
