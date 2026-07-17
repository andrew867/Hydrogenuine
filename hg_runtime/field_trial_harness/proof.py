"""Proof bundle helpers for Phase 35."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), sort_keys=True) + "\n")


def secret_redaction_audit(payloads: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    import re

    pattern = re.compile(r"(api[_-]?key|secret|password|bearer|sk-[a-zA-Z0-9]{8,})", re.I)
    hits: list[str] = []
    for payload in payloads:
        text = json.dumps(payload)
        if pattern.search(text) and "redact" not in text.lower() and "forbidden" not in text.lower():
            hits.append("possible_secret_leak")
    return {"passed": not hits, "hits": hits}


__all__ = ["secret_redaction_audit", "write_json", "write_jsonl"]
