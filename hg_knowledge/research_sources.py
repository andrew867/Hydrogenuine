from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def load_source_config() -> dict[str, Any]:
    try:
        from hg_knowledge.control_plane import load_source_config as load_control_plane_source_config

        return load_control_plane_source_config()
    except Exception:
        return {
            "brave": {"enabled": True, "news_count": 4, "web_count": 5},
            "google_news": {"enabled": False, "news_count": 4, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            "local_news": {"enabled": False, "urls": [], "timeout_s": 8},
        }


def _normalized_news_item(row: dict[str, Any], *, source_name: str, category: str = "") -> dict[str, Any] | None:
    title = str(row.get("title") or "").strip()
    url = str(row.get("url") or row.get("link") or "").strip()
    description = str(row.get("description") or row.get("snippet") or row.get("summary") or "").strip()
    if not title or not url:
        return None
    normalized = dict(row)
    normalized["title"] = title
    normalized["url"] = url
    if description:
        normalized["description"] = description
    normalized["source_name"] = source_name
    if category and not normalized.get("category"):
        normalized["category"] = category
    return normalized


def _dedupe_news_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "").strip().lower()
        title = str(row.get("title") or "").strip().lower()
        if not url or not title:
            continue
        if url in seen_urls or title in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title)
        out.append(row)
    return out


def _brave_news(query: str, *, count: int) -> list[dict[str, Any]]:
    try:
        from hg_realtime.integrations.search_tools import _run_brave_search

        rows = _run_brave_search("news", query=query, count=count, freshness="pw", method="GET")
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = _normalized_news_item(row, source_name="brave")
        if item is not None:
            out.append(item)
    return out


def _local_news(query: str, *, urls: list[str], timeout_s: int = 8) -> list[dict[str, Any]]:
    if not urls:
        return []
    query_terms = [part.strip().lower() for part in query.split() if part.strip()]
    out: list[dict[str, Any]] = []
    for url in urls:
        source_url = str(url or "").strip()
        if not source_url:
            continue
        try:
            with urllib.request.urlopen(source_url, timeout=max(2, int(timeout_s))) as response:
                raw = response.read()
        except Exception:
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for item in items:
            title = (item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link = (item.findtext("link") or item.findtext("{http://www.w3.org/2005/Atom}link") or "").strip()
            if not link:
                atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                if atom_link is not None:
                    link = str(atom_link.attrib.get("href") or "").strip()
            description = (
                item.findtext("description")
                or item.findtext("summary")
                or item.findtext("{http://www.w3.org/2005/Atom}summary")
                or ""
            ).strip()
            searchable = f"{title} {description}".lower()
            if query_terms and not all(term in searchable for term in query_terms[:3]):
                continue
            normalized = _normalized_news_item(
                {"title": title, "url": link, "description": description},
                source_name="local_news",
            )
            if normalized is not None:
                out.append(normalized)
    return out


def _google_news_rss(query: str, *, count: int, hl: str = "en-US", gl: str = "US", ceid: str = "US:en", timeout_s: int = 8) -> list[dict[str, Any]]:
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={urllib.parse.quote(hl)}&gl={urllib.parse.quote(gl)}&ceid={urllib.parse.quote(ceid)}"
    try:
        with urllib.request.urlopen(url, timeout=max(2, int(timeout_s))) as response:
            raw = response.read()
    except Exception:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    out: list[dict[str, Any]] = []
    for item in root.findall(".//item")[: max(1, count)]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        normalized = _normalized_news_item(
            {"title": title, "url": link, "description": description},
            source_name="google_news",
        )
        if normalized is not None:
            out.append(normalized)
    return out


def search_news(query: str, *, count: int = 8) -> list[dict[str, Any]]:
    config = load_source_config()
    results: list[dict[str, Any]] = []
    brave_cfg = config.get("brave") if isinstance(config.get("brave"), dict) else {}
    if brave_cfg.get("enabled", True):
        results.extend(_brave_news(query, count=max(1, int(brave_cfg.get("news_count") or count))))
    google_cfg = config.get("google_news") if isinstance(config.get("google_news"), dict) else {}
    if google_cfg.get("enabled"):
        results.extend(
            _google_news_rss(
                query,
                count=max(1, int(google_cfg.get("news_count") or count)),
                hl=str(google_cfg.get("hl") or "en-US"),
                gl=str(google_cfg.get("gl") or "US"),
                ceid=str(google_cfg.get("ceid") or "US:en"),
                timeout_s=int(google_cfg.get("timeout_s") or 8),
            )
        )
    local_cfg = config.get("local_news") if isinstance(config.get("local_news"), dict) else {}
    if local_cfg.get("enabled") and isinstance(local_cfg.get("urls"), list):
        results.extend(
            _local_news(
                query,
                urls=[str(item) for item in local_cfg.get("urls", []) if str(item).strip()],
                timeout_s=int(local_cfg.get("timeout_s") or 8),
            )
        )
    return _dedupe_news_results(results)[: max(1, count)]


def search_web(query: str, *, count: int = 5) -> list[dict[str, Any]]:
    config = load_source_config()
    brave_cfg = config.get("brave") if isinstance(config.get("brave"), dict) else {}
    if not brave_cfg.get("enabled", True):
        return []
    effective_count = max(1, int(brave_cfg.get("web_count") or count))
    try:
        from hg_realtime.integrations.search_tools import _run_brave_search

        rows = _run_brave_search("web", query=query, count=effective_count, method="GET")
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized = _normalized_news_item(row, source_name="brave")
        if normalized is not None:
            out.append(normalized)
    return out[:effective_count]


def probe_sources(query: str, *, news_count: int = 3, web_count: int = 3) -> dict[str, Any]:
    config = load_source_config()
    brave_cfg = config.get("brave") if isinstance(config.get("brave"), dict) else {}
    google_cfg = config.get("google_news") if isinstance(config.get("google_news"), dict) else {}
    local_cfg = config.get("local_news") if isinstance(config.get("local_news"), dict) else {}
    sources: dict[str, Any] = {}

    brave_enabled = bool(brave_cfg.get("enabled", True))
    brave_news = _brave_news(query, count=max(1, int(brave_cfg.get("news_count") or news_count))) if brave_enabled else []
    brave_web = []
    if brave_enabled:
        try:
            brave_web = search_web(query, count=max(1, int(brave_cfg.get("web_count") or web_count)))
        except Exception:
            brave_web = []
    sources["brave"] = {
        "enabled": brave_enabled,
        "news_count": len(brave_news),
        "web_count": len(brave_web),
        "sample_titles": [str(item.get("title") or "").strip() for item in (brave_news[:2] + brave_web[:2]) if str(item.get("title") or "").strip()][:3],
    }

    google_enabled = bool(google_cfg.get("enabled", False))
    google_results = (
        _google_news_rss(
            query,
            count=max(1, int(google_cfg.get("news_count") or news_count)),
            hl=str(google_cfg.get("hl") or "en-US"),
            gl=str(google_cfg.get("gl") or "US"),
            ceid=str(google_cfg.get("ceid") or "US:en"),
            timeout_s=int(google_cfg.get("timeout_s") or 8),
        )
        if google_enabled
        else []
    )
    sources["google_news"] = {
        "enabled": google_enabled,
        "news_count": len(google_results),
        "sample_titles": [str(item.get("title") or "").strip() for item in google_results[:3] if str(item.get("title") or "").strip()],
    }

    local_enabled = bool(local_cfg.get("enabled", False))
    local_urls = [str(item) for item in local_cfg.get("urls", []) if str(item).strip()] if isinstance(local_cfg.get("urls"), list) else []
    local_results = _local_news(query, urls=local_urls, timeout_s=int(local_cfg.get("timeout_s") or 8)) if local_enabled else []
    sources["local_news"] = {
        "enabled": local_enabled,
        "url_count": len(local_urls),
        "news_count": len(local_results),
        "sample_titles": [str(item.get("title") or "").strip() for item in local_results[:3] if str(item.get("title") or "").strip()],
    }

    return {
        "query": query,
        "sources": sources,
    }
