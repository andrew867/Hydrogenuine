from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from hg_knowledge import research_sources
from hg_knowledge.control_plane import save_source_config


def test_search_news_merges_and_dedupes_brave_and_local_sources(tmp_path: Path):
    rss = b"""<?xml version="1.0"?>
<rss><channel>
  <item><title>Agent governance update</title><link>https://example.com/news</link><description>Duplicate headline</description></item>
  <item><title>Local labour story</title><link>https://local.test/labour</link><description>Agent labour organizing</description></item>
</channel></rss>"""

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return rss

    with (
        patch.dict(os.environ, {"HG_GATEWAY_DB_PATH": str(tmp_path / "memory" / "gateway.sqlite3")}),
        patch.object(research_sources, "_workspace_root", return_value=tmp_path),
        patch("hg_realtime.integrations.search_tools._run_brave_search", return_value=[
            {"title": "Agent governance update", "url": "https://example.com/news", "description": "Primary"},
            {"title": "Inference cost shift", "url": "https://example.com/costs", "description": "Secondary"},
        ]),
        patch("urllib.request.urlopen", return_value=_Resp()),
    ):
        save_source_config({"brave": {"enabled": True, "news_count": 4}, "local_news": {"enabled": True, "urls": ["https://local.test/rss.xml"], "timeout_s": 2}})
        results = research_sources.search_news("agent", count=6)

    titles = [item["title"] for item in results]
    assert "Agent governance update" in titles
    assert "Inference cost shift" in titles
    assert "Local labour story" in titles
    assert titles.count("Agent governance update") == 1


def test_search_web_uses_brave_config_count(tmp_path: Path):
    captured: dict[str, int] = {}

    def _fake_brave(kind: str, *, query: str, count: int, method: str = "GET", freshness=None):
        captured["count"] = count
        return [
            {"title": "Topic one", "url": "https://example.com/1", "description": "A"},
            {"title": "Topic two", "url": "https://example.com/2", "description": "B"},
            {"title": "Topic three", "url": "https://example.com/3", "description": "C"},
        ]

    with (
        patch.dict(os.environ, {"HG_GATEWAY_DB_PATH": str(tmp_path / "memory" / "gateway.sqlite3")}),
        patch.object(research_sources, "_workspace_root", return_value=tmp_path),
        patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_brave),
    ):
        save_source_config({"brave": {"enabled": True, "web_count": 2}})
        results = research_sources.search_web("agent infra", count=5)

    assert captured["count"] == 2
    assert len(results) == 2


def test_search_news_includes_google_news_rss_when_enabled(tmp_path: Path):
    rss = b"""<?xml version="1.0"?>
<rss><channel>
  <item><title>Google sourced topic</title><link>https://news.example.com/topic</link><description>Snippet</description></item>
  <item><title>Second topic</title><link>https://news.example.com/second</link><description>Snippet 2</description></item>
</channel></rss>"""

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return rss

    with (
        patch.dict(os.environ, {"HG_GATEWAY_DB_PATH": str(tmp_path / "memory" / "gateway.sqlite3")}),
        patch.object(research_sources, "_workspace_root", return_value=tmp_path),
        patch("urllib.request.urlopen", return_value=_Resp()),
    ):
        save_source_config({"brave": {"enabled": False}, "google_news": {"enabled": True, "news_count": 2, "hl": "en-US", "gl": "US", "ceid": "US:en"}, "local_news": {"enabled": False}})
        results = research_sources.search_news("agent sovereignty", count=4)

    assert len(results) == 2
    assert results[0]["source_name"] == "google_news"
    assert {item["title"] for item in results} == {"Google sourced topic", "Second topic"}


def test_probe_sources_reports_enabled_source_counts(tmp_path: Path):
    rss = b"""<?xml version="1.0"?>
<rss><channel>
  <item><title>Agent infra local topic</title><link>https://local.test/topic</link><description>Agent infra snippet</description></item>
</channel></rss>"""

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return rss

    with (
        patch.dict(os.environ, {"HG_GATEWAY_DB_PATH": str(tmp_path / "memory" / "gateway.sqlite3")}),
        patch.object(research_sources, "_workspace_root", return_value=tmp_path),
        patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=[
            [{"title": "Brave news", "url": "https://example.com/news", "description": "news"}],
            [{"title": "Brave web", "url": "https://example.com/web", "description": "web"}],
        ]),
        patch.object(research_sources, "_google_news_rss", return_value=[{"title": "Google news", "url": "https://news.example.com/topic", "source_name": "google_news"}]),
        patch("urllib.request.urlopen", return_value=_Resp()),
    ):
        save_source_config({"brave": {"enabled": True, "news_count": 2, "web_count": 2}, "google_news": {"enabled": True, "news_count": 1, "hl": "en-US", "gl": "US", "ceid": "US:en"}, "local_news": {"enabled": True, "urls": ["https://local.test/rss.xml"], "timeout_s": 2}})
        result = research_sources.probe_sources("agent infra")

    assert result["sources"]["brave"]["news_count"] == 1
    assert result["sources"]["brave"]["web_count"] == 1
    assert result["sources"]["google_news"]["news_count"] == 1
    assert result["sources"]["local_news"]["news_count"] == 1
