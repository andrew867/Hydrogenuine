"""OBT bundle discovery helpers for gate-integrity checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

TS_RE = re.compile(r"^\d{8}T\d{6}Z$")


TS_RE = re.compile(r"^\d{8}T\d{6}Z$")


def _sorted_bundles(pack_dir: Path) -> list[Path]:
    if not pack_dir.is_dir():
        return []
    return sorted(p for p in pack_dir.iterdir() if p.is_dir() and TS_RE.match(p.name))


def load_truth_report(bundle: Path) -> dict | None:
    report_path = bundle / "truth_gate_report.json"
    if not report_path.is_file():
        return None
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def find_obt_strict_green_bundle(pack_dir: Path) -> Path | None:
    for bundle in reversed(_sorted_bundles(pack_dir)):
        report = load_truth_report(bundle)
        if report and report.get("verdict") == "green" and report.get("strict_ct_mode"):
            return bundle
    return None


def find_obt_default_skip_bundle(pack_dir: Path) -> Path | None:
    """Latest default-mode bundle that records skips (green_with_skips evidence)."""
    for bundle in reversed(_sorted_bundles(pack_dir)):
        report = load_truth_report(bundle)
        if not report or report.get("strict_ct_mode"):
            continue
        if report.get("skips") and report.get("verdict") in {"green_with_skips", "green_fast"}:
            return bundle
    return None


__all__ = [
    "TS_RE",
    "find_obt_default_skip_bundle",
    "find_obt_strict_green_bundle",
    "load_truth_report",
]
