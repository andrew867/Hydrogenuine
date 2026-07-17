"""Secret and canary scanning for proof bundles and audit scripts (CT-02)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hg_core.secrets.canary import contains_canary, find_canaries_in_text
from hg_core.secrets.redact import contains_raw_secret_pattern

DEFAULT_SCAN_EXTENSIONS = frozenset({".json", ".jsonl", ".md", ".txt", ".log", ".yaml", ".yml"})


def scan_text(text: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if contains_canary(text):
        for marker in find_canaries_in_text(text):
            hits.append({"kind": "canary", "match": marker})
    if contains_raw_secret_pattern(text):
        hits.append({"kind": "secret_pattern", "match": "raw_secret_pattern"})
    return hits


def scan_file(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [{"kind": "missing", "match": str(path)}]
    file_hits = scan_text(text)
    for item in file_hits:
        item["file"] = str(path)
    return file_hits


def scan_directory(
    root: Path,
    *,
    extensions: frozenset[str] = DEFAULT_SCAN_EXTENSIONS,
) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if not root.exists():
        return [{"kind": "missing_evidence", "match": str(root)}]
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in extensions and path.name not in {"command_log.jsonl"}:
            continue
        hits.extend(scan_file(path))
    return hits


def manifest_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


__all__ = ["DEFAULT_SCAN_EXTENSIONS", "manifest_hash", "scan_directory", "scan_file", "scan_text"]
