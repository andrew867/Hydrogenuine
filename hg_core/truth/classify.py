"""Computed subsystem classification for OBT stage 9 — never hand-written."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from hg_plt.classifier import classify_subsystems

_STATUS_MAP = {
    "REAL": "implemented",
    "GATED": "scaffold",
    "SCAFFOLD": "scaffold",
    "STUB": "stubbed",
    "DISABLED": "stubbed",
    "DEGRADED": "scaffold",
    "FAILED": "stubbed",
    "FUTURE_PHASE": "absent",
}

_STUB_MARKERS = (
    re.compile(r"\braise\s+NotImplementedError\b"),
    re.compile(r"\bNotImplemented\b"),
    re.compile(r"\bplaceholder\b", re.IGNORECASE),
)


def static_stub_scan(workspace: Path, *, roots: tuple[str, ...] = ("hg_runtime", "hg_core")) -> dict[str, list[str]]:
    """Scan runtime/core trees for stub markers in non-test Python files."""
    findings: dict[str, list[str]] = {}
    for root_name in roots:
        root = workspace / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            rel = path.relative_to(workspace).as_posix()
            if "/tests/" in rel or rel.startswith("tests/"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            hits: list[str] = []
            for marker in _STUB_MARKERS:
                if marker.search(text):
                    hits.append(marker.pattern)
            if hits:
                findings[rel] = hits
    return findings


def classify_subsystems_truth(
    *,
    workspace: Path,
    replay_ok: bool | None = None,
    world_state: Mapping[str, Any] | None = None,
    static_findings: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Merge PLT classifier with static scan — downgrade claimed REAL if stubs found."""
    static = static_findings if static_findings is not None else static_stub_scan(workspace)
    stub_modules = set(static.keys())
    rows: list[dict[str, Any]] = []
    for item in classify_subsystems(replay_ok=replay_ok, world_state=world_state):
        status = _STATUS_MAP.get(item.status, "scaffold")
        evidence: list[str] = [f"plt_classifier:{item.status}"]
        for mod in stub_modules:
            if item.subsystem.lower().replace(" ", "_") in mod.lower():
                status = "stubbed"
                evidence.append(f"static_scan:{mod}")
        rows.append(
            {
                "subsystem": item.subsystem,
                "status": status,
                "works": list(item.works),
                "blocked": list(item.blocked),
                "report_ref": item.report_ref,
                "evidence": evidence,
            }
        )
    if static and not any(r["status"] == "stubbed" for r in rows):
        rows.append(
            {
                "subsystem": "static_scan",
                "status": "stubbed",
                "works": [],
                "blocked": ["stub markers in runtime/core modules"],
                "report_ref": None,
                "evidence": [f"{k}:{v}" for k, v in sorted(static.items())[:5]],
            }
        )
    return rows


__all__ = ["classify_subsystems_truth", "static_stub_scan"]
