"""Proof bundle discovery for pack closure checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

TS_RE = re.compile(r"^\d{8}T\d{6}Z$")


def sorted_timestamp_bundles(pack_dir: Path) -> list[Path]:
    if not pack_dir.is_dir():
        return []
    return sorted(p for p in pack_dir.iterdir() if p.is_dir() and TS_RE.match(p.name))


def load_gate_result(bundle: Path) -> dict | None:
    gate_path = bundle / "gate_result.json"
    if not gate_path.is_file():
        return None
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def find_latest_green_gate_bundle(workspace: Path, *path_parts: str) -> Path | None:
    pack_dir = workspace.joinpath("docs", "proofs", "connective_tissue", *path_parts)
    for bundle in reversed(sorted_timestamp_bundles(pack_dir)):
        result = load_gate_result(bundle)
        if result and result.get("ok"):
            return bundle
    return None


__all__ = [
    "TS_RE",
    "find_latest_green_gate_bundle",
    "load_gate_result",
    "sorted_timestamp_bundles",
]
