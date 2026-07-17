"""Session index and timeline builder."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.openvino_watchtower.session import SESSIONS_ROOT, list_sessions

WORKSPACE = Path(__file__).resolve().parents[2]
INDEX_PATH = WORKSPACE / ".hg-local" / "openvino_watchtower" / "sessions_index.json"


@dataclass
class WatchtowerTimelineIndex:
    session_id: str
    entries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "entries": self.entries}


def build_timeline_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for ev in events:
        timeline.append(
            {
                "ts": ev.get("ts"),
                "event_type": ev.get("event_type"),
                "span_id": ev.get("span_id"),
                "organ_id": ev.get("organ_id"),
                "severity": _severity(ev),
            }
        )
    return timeline


def _severity(ev: dict[str, Any]) -> str:
    et = str(ev.get("event_type", ""))
    if "FAILED" in et or "CONTACT_LOST" in et or "STALE" in et:
        return "RED"
    if "STALE" in et or "WARNING" in et:
        return "YELLOW"
    return "GREEN"


def refresh_index(*, root: Path | None = None) -> dict[str, Any]:
    sessions = list_sessions(root=root)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_count": len(sessions),
        "sessions": sessions,
        "authority_created": False,
        "permission_granted": False,
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def read_index() -> dict[str, Any]:
    if not INDEX_PATH.is_file():
        return refresh_index()
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return refresh_index()


__all__ = [
    "INDEX_PATH",
    "WatchtowerTimelineIndex",
    "build_timeline_from_events",
    "read_index",
    "refresh_index",
]
