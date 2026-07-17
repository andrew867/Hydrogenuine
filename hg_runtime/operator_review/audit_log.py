"""Append-only operator review audit log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.operator_review.errors import ReviewStoreError
from hg_runtime.operator_review.redaction import has_forbidden_review_field


def append_audit_entry(path: Path, entry: dict[str, Any]) -> None:
    if has_forbidden_review_field(entry):
        raise ReviewStoreError("audit entry contains forbidden field")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def read_audit_log(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


__all__ = ["append_audit_entry", "read_audit_log"]
