"""Audit decision timeline from local receipts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


def _read_jsonl(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def build_decision_timeline(*, workspace: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ws = workspace or WORKSPACE
    events: list[dict[str, Any]] = []

    for path, kind in (
        (ws / ".hg-local" / "exciton" / "control_receipts.jsonl", "control"),
        (ws / ".hg-local" / "operator_action_queue" / "operator_action_receipts.jsonl", "queue"),
        (ws / ".hg-local" / "soak" / "stop_panic_receipts.jsonl", "stop_panic"),
    ):
        for row in _read_jsonl(path):
            events.append({
                "kind": kind,
                "ts": row.get("created_at") or row.get("ts"),
                "human_summary": row.get("human_message") or row.get("decision") or kind,
                "receipt_ref": row.get("receipt_id"),
                "severity": "RED" if "panic" in str(row).lower() else "INFO",
            })

    events.sort(key=lambda e: str(e.get("ts") or ""))
    return events[-limit:]


__all__ = ["build_decision_timeline"]
