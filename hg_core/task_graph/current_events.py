"""Current-events pulse helpers — brief freshness + headline queue for social wakes."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

HEADLINE_QUEUE_REL = Path("memory/automation/current_events/headline_queue.json")
BRIEF_DIR_REL = Path("knowledge/current_events")
DEFAULT_MIN_REFRESH_HOURS = 6.0


def current_events_pulse_enabled() -> bool:
    raw = os.environ.get("CURRENT_EVENTS_PULSE_ENABLED", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def headline_queue_path(workspace: Path) -> Path:
    return workspace / HEADLINE_QUEUE_REL


def _latest_brief_path(workspace: Path) -> Path | None:
    brief_dir = workspace / BRIEF_DIR_REL
    if not brief_dir.is_dir():
        return None
    candidates = sorted(brief_dir.glob("brief-*.md"), reverse=True)
    return candidates[0] if candidates else None


def _brief_age_hours(path: Path) -> float | None:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        return (datetime.now(UTC) - mtime).total_seconds() / 3600.0
    except OSError:
        return None


def _parse_headlines_from_brief(text: str) -> list[dict[str, Any]]:
    headlines: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.match(
            r"^\d+\.\s+\*\*(.+?)\*\*\s+-\s+(https?://\S+)(?:\s+\[([^\]]+)\])?",
            line.strip(),
        )
        if not match:
            continue
        headlines.append(
            {
                "title": match.group(1).strip(),
                "url": match.group(2).strip(),
                "category": (match.group(3) or "general").strip(),
            }
        )
    return headlines


def load_headline_queue(workspace: Path) -> list[dict[str, Any]]:
    path = headline_queue_path(workspace)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("headlines") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def save_headline_queue(workspace: Path, headlines: list[dict[str, Any]]) -> Path:
    path = headline_queue_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headlines": headlines[:30],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def refresh_current_events(
    workspace: Path,
    *,
    force: bool = False,
    min_refresh_hours: float = DEFAULT_MIN_REFRESH_HOURS,
) -> dict[str, Any]:
    if not current_events_pulse_enabled():
        return {"refreshed": False, "reason": "pulse_disabled", "headlines": []}
    brief_path = _latest_brief_path(workspace)
    if brief_path is None:
        return {"refreshed": False, "reason": "no_brief", "headlines": []}
    age = _brief_age_hours(brief_path)
    if not force and age is not None and age < min_refresh_hours:
        return {
            "refreshed": False,
            "reason": "brief_fresh",
            "brief_path": str(brief_path),
            "age_hours": age,
            "headlines": load_headline_queue(workspace),
        }
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return {"refreshed": False, "reason": "brief_read_error", "headlines": []}
    headlines = _parse_headlines_from_brief(text)
    if headlines:
        save_headline_queue(workspace, headlines)
    return {
        "refreshed": True,
        "reason": "refreshed",
        "brief_path": str(brief_path),
        "headlines": headlines,
        "headline_count": len(headlines),
    }


def _fatigued_titles(workspace: Path, platform: str) -> set[str]:
    titles: set[str] = set()
    try:
        from hg_core.task_graph.social_outbound_learning import load_active_lessons

        for lesson in load_active_lessons(workspace, platform=platform, limit=20):
            snippet = str(lesson.get("body_snippet") or "").lower()
            if snippet:
                titles.add(snippet[:80])
    except Exception:
        pass
    return titles


def select_news_angle(
    workspace: Path,
    *,
    platform: str = "moltbook",
    exclude_fatigued: bool = True,
) -> dict[str, Any]:
    headlines = load_headline_queue(workspace)
    if not headlines:
        refresh_current_events(workspace, force=False)
        headlines = load_headline_queue(workspace)
    fatigued = _fatigued_titles(workspace, platform) if exclude_fatigued else set()
    preferred_categories = {
        "moltbook": {"technology", "philosophy", "science", "business"},
        "fourclaw": {"technology", "world", "philosophy"},
    }.get(platform.lower(), {"technology", "world", "business"})
    for row in headlines:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        lower = title.lower()
        if exclude_fatigued and any(f in lower for f in fatigued):
            continue
        category = str(row.get("category") or "general").strip().lower()
        if category in preferred_categories or not preferred_categories:
            return {
                "title": title,
                "url": str(row.get("url") or ""),
                "category": category,
                "topic_hint": title[:120],
            }
    if headlines:
        row = headlines[0]
        return {
            "title": str(row.get("title") or ""),
            "url": str(row.get("url") or ""),
            "category": str(row.get("category") or "general"),
            "topic_hint": str(row.get("title") or "")[:120],
        }
    return {"title": "", "url": "", "category": "", "topic_hint": ""}


def headline_bullets(workspace: Path, *, limit: int = 5) -> str:
    headlines = load_headline_queue(workspace)
    if not headlines:
        return ""
    lines = []
    for row in headlines[:limit]:
        title = str(row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if title:
            lines.append(f"- {title}" + (f" ({url})" if url else ""))
    return "\n".join(lines)


__all__ = [
    "current_events_pulse_enabled",
    "headline_bullets",
    "headline_queue_path",
    "load_headline_queue",
    "refresh_current_events",
    "save_headline_queue",
    "select_news_angle",
]
