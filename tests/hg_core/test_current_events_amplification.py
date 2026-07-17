from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from hg_core.task_graph.current_events import (
    headline_queue_path,
    load_headline_queue,
    refresh_current_events,
    save_headline_queue,
    select_news_angle,
)
from hg_core.task_graph import native_task_tools as ntt


def _seed_brief(workspace: Path, *, stale: bool = False) -> Path:
    brief_dir = workspace / "knowledge/current_events"
    brief_dir.mkdir(parents=True)
    path = brief_dir / "brief-2026-06-11.md"
    path.write_text(
        "## Headlines\n\n"
        "1. **AI regulation heats up in Brussels** - https://example.com/ai-reg [Technology]\n"
        "2. **Markets shrug at oil spike** - https://example.com/oil [Business]\n",
        encoding="utf-8",
    )
    if stale:
        old = datetime(2020, 1, 1, tzinfo=UTC).timestamp()
        path.touch()
        import os

        os.utime(path, (old, old))
    return path


def test_refresh_skips_when_brief_fresh(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _seed_brief(tmp_path, stale=False)
    result = refresh_current_events(tmp_path, force=False, min_refresh_hours=6)
    assert result["refreshed"] is False
    assert result["reason"] == "brief_fresh"


def test_refresh_writes_headline_queue_when_stale(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _seed_brief(tmp_path, stale=True)
    result = refresh_current_events(tmp_path, force=False, min_refresh_hours=6)
    assert result["refreshed"] is True
    queue = load_headline_queue(tmp_path)
    assert len(queue) >= 2
    assert headline_queue_path(tmp_path).is_file()


def test_select_news_angle_excludes_fatigued(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_headline_queue(
        tmp_path,
        [
            {"title": "AI regulation heats up in Brussels", "url": "https://example.com/ai-reg", "category": "Technology"},
            {"title": "Markets shrug at oil spike", "url": "https://example.com/oil", "category": "Business"},
        ],
    )
    lessons_dir = tmp_path / "memory/automation/outbound_lessons"
    lessons_dir.mkdir(parents=True)
    (lessons_dir / "global.jsonl").write_text(
        json.dumps(
            {
                "lesson_id": "les_test",
                "recorded_at": "2026-06-11T10:00:00Z",
                "platform": "moltbook",
                "kind": "template_bloat",
                "severity": "high",
                "status": "active",
                "body_snippet": "AI regulation heats up in Brussels",
                "recurrence_key": "x",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    angle = select_news_angle(tmp_path, platform="moltbook", exclude_fatigued=True)
    assert "oil" in angle["title"].lower()


def test_knowledge_wake_briefing_includes_headline_bullets(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_headline_queue(
        tmp_path,
        [{"title": "Test headline", "url": "https://example.com/x", "category": "Technology"}],
    )
    briefing = ntt._knowledge_wake_briefing(tmp_path, "knowledge-research-auto-v2")
    assert "Headline bullets" in briefing
    assert "Test headline" in briefing


def test_refresh_force_bypasses_skip(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _seed_brief(tmp_path, stale=False)
    result = refresh_current_events(tmp_path, force=True, min_refresh_hours=6)
    assert result["refreshed"] is True


def test_corrupt_headline_queue_returns_empty(tmp_path: Path):
    path = headline_queue_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert load_headline_queue(tmp_path) == []
