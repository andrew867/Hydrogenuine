"""Knowledge service using shared gateway DB mirror."""

from __future__ import annotations

import json
import re
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection
from hg_realtime.scheduler.schedule_config import load_schedule
from hg_knowledge.control_plane import (
    clear_queue_topics as cp_clear_queue_topics,
    get_control_plane_state as cp_get_control_plane_state,
    load_research_history,
    load_source_config as cp_load_source_config,
    list_queue_topics as cp_list_queue_topics,
    queue_topic as cp_queue_topic,
    remove_queue_topic as cp_remove_queue_topic,
    save_source_config as cp_save_source_config,
)

REALTIME_SCHEDULE_PATH = Path("memory") / "automation" / "realtime_schedule.json"
RESEARCH_JOB_ID = "knowledge-research-auto-v2"
DEFAULT_RESEARCH_SCHEDULE_ENTRY = {
    "job_id": RESEARCH_JOB_ID,
    "interval_minutes": 15,
    "inputs": {
        "trigger": "realtime",
        "goal": "",
    },
}
RESEARCH_DOMAIN_SPECS: tuple[dict[str, str], ...] = (
    {"key": "world", "title": "World", "category": "politics"},
    {"key": "politics", "title": "Politics", "category": "politics"},
    {"key": "business", "title": "Business", "category": "economics"},
    {"key": "finance", "title": "Finance", "category": "economics"},
    {"key": "technology", "title": "Technology", "category": "technology"},
    {"key": "ai", "title": "AI", "category": "technology"},
    {"key": "science", "title": "Science", "category": "science"},
    {"key": "health", "title": "Health", "category": "health"},
    {"key": "space", "title": "Space", "category": "science"},
    {"key": "philosophy", "title": "Philosophy", "category": "philosophy"},
    {"key": "ethics", "title": "Ethics", "category": "philosophy"},
    {"key": "humanity", "title": "Humanity", "category": "humanity"},
    {"key": "society", "title": "Society", "category": "humanity"},
    {"key": "psychology", "title": "Psychology", "category": "psychology"},
    {"key": "culture", "title": "Culture", "category": "culture"},
    {"key": "arts", "title": "Arts", "category": "arts"},
    {"key": "history", "title": "History", "category": "history"},
    {"key": "religion", "title": "Religion", "category": "religion"},
    {"key": "law", "title": "Law", "category": "law"},
    {"key": "education", "title": "Education", "category": "education"},
    {"key": "environment", "title": "Environment", "category": "environment"},
    {"key": "media", "title": "Media", "category": "media"},
)


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return Path.cwd()


def _gateway_db_path() -> str | None:
    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    root = _workspace_root()
    if not root:
        return None
    return str((root / "memory" / "gateway.sqlite3").resolve())


def _current_events_dir() -> Path:
    return _workspace_root() / "knowledge" / "current_events"


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def list_queue_topics() -> list[dict[str, Any]]:
    return cp_list_queue_topics()


def queue_topic(topic: str, *, requested_by: str = "", priority: str = "medium", context: str = "") -> dict[str, Any]:
    return cp_queue_topic(topic, requested_by=requested_by, priority=priority, context=context)


def remove_queue_topic(topic: str) -> dict[str, Any]:
    return cp_remove_queue_topic(topic)


def clear_queue_topics() -> dict[str, Any]:
    return cp_clear_queue_topics()


def get_research_schedule() -> dict[str, Any]:
    state = load_schedule(_workspace_root())
    entry = next((item for item in state.entries if str(item.job_id or "").strip() == RESEARCH_JOB_ID), None)
    enabled = entry is not None
    effective_entry = {
        "job_id": RESEARCH_JOB_ID,
        "interval_minutes": 15,
        "inputs": dict(DEFAULT_RESEARCH_SCHEDULE_ENTRY["inputs"]),
    }
    if entry is not None:
        effective_entry = {
            "job_id": entry.job_id,
            "cron": entry.cron,
            "interval_minutes": entry.interval_minutes,
            "inputs": dict(entry.inputs or {}),
        }
    return {
        "job_id": RESEARCH_JOB_ID,
        "enabled": enabled,
        "entry": effective_entry,
    }


def set_research_schedule_enabled(enabled: bool) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with get_connection(_gateway_db_path()) as conn:
        if enabled:
            existing = conn.execute(
                "SELECT created_at FROM scheduled_jobs WHERE tenant_id = ? AND job_id = ?",
                ("default", RESEARCH_JOB_ID),
            ).fetchone()
            created_at = str(existing[0]) if existing else now
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_jobs (
                    tenant_id, job_id, cron, interval_minutes, inputs_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    "default",
                    RESEARCH_JOB_ID,
                    None,
                    DEFAULT_RESEARCH_SCHEDULE_ENTRY["interval_minutes"],
                    json.dumps(DEFAULT_RESEARCH_SCHEDULE_ENTRY["inputs"]),
                    created_at,
                    now,
                ),
            )
        else:
            existing = conn.execute(
                "SELECT job_id FROM scheduled_jobs WHERE tenant_id = ? AND job_id = ?",
                ("default", RESEARCH_JOB_ID),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE scheduled_jobs
                    SET status = 'paused', updated_at = ?
                    WHERE tenant_id = ? AND job_id = ?
                    """,
                    (now, "default", RESEARCH_JOB_ID),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO scheduled_jobs (
                        tenant_id, job_id, cron, interval_minutes, inputs_json, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'paused', ?, ?)
                    """,
                    (
                        "default",
                        RESEARCH_JOB_ID,
                        None,
                        DEFAULT_RESEARCH_SCHEDULE_ENTRY["interval_minutes"],
                        json.dumps(DEFAULT_RESEARCH_SCHEDULE_ENTRY["inputs"]),
                        now,
                        now,
                    ),
                )
    return {"ok": True, **get_research_schedule()}


def get_domain_specs() -> list[dict[str, str]]:
    return [dict(item) for item in RESEARCH_DOMAIN_SPECS]


def get_source_config_state() -> dict[str, Any]:
    config = cp_load_source_config()
    brave = config.get("brave") if isinstance(config.get("brave"), dict) else {}
    google_news = config.get("google_news") if isinstance(config.get("google_news"), dict) else {}
    local_news = config.get("local_news") if isinstance(config.get("local_news"), dict) else {}
    urls = local_news.get("urls") if isinstance(local_news.get("urls"), list) else []
    return {
        "sources": {
            "brave": {
                "enabled": bool(brave.get("enabled", True)),
                "news_count": int(brave.get("news_count") or 4),
                "web_count": int(brave.get("web_count") or 5),
            },
            "google_news": {
                "enabled": bool(google_news.get("enabled", False)),
                "news_count": int(google_news.get("news_count") or 4),
                "hl": str(google_news.get("hl") or "en-US"),
                "gl": str(google_news.get("gl") or "US"),
                "ceid": str(google_news.get("ceid") or "US:en"),
            },
            "local_news": {
                "enabled": bool(local_news.get("enabled", False)),
                "url_count": len([item for item in urls if str(item).strip()]),
                "urls": [str(item) for item in urls if str(item).strip()],
                "timeout_s": int(local_news.get("timeout_s") or 8),
            },
        }
    }


def save_source_config_state(payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    sources = payload.get("sources") if isinstance(payload.get("sources"), dict) else {}
    merged = cp_save_source_config(sources)
    return {
        "sources": {
            "brave": {
                "enabled": bool(merged["brave"].get("enabled", True)),
                "news_count": int(merged["brave"].get("news_count") or 4),
                "web_count": int(merged["brave"].get("web_count") or 5),
            },
            "google_news": {
                "enabled": bool(merged["google_news"].get("enabled", False)),
                "news_count": int(merged["google_news"].get("news_count") or 4),
                "hl": str(merged["google_news"].get("hl") or "en-US"),
                "gl": str(merged["google_news"].get("gl") or "US"),
                "ceid": str(merged["google_news"].get("ceid") or "US:en"),
            },
            "local_news": {
                "enabled": bool(merged["local_news"].get("enabled", False)),
                "url_count": len([item for item in merged["local_news"].get("urls", []) if str(item).strip()]),
                "urls": [str(item) for item in merged["local_news"].get("urls", []) if str(item).strip()],
                "timeout_s": int(merged["local_news"].get("timeout_s") or 8),
            },
        }
    }


def probe_source_config(query: str) -> dict[str, Any]:
    effective_query = str(query or "").strip() or "AI agents infrastructure current events"
    try:
        from hg_knowledge.research_sources import probe_sources

        return probe_sources(effective_query)
    except Exception:
        return {
            "query": effective_query,
            "sources": {},
        }


def get_control_plane_state() -> dict[str, Any]:
    queue = list_queue_topics()
    schedule = get_research_schedule()
    state = cp_get_control_plane_state()
    return {
        "queue_count": len(queue),
        "queued_topics": queue,
        "schedule": schedule,
        "domain_specs": get_domain_specs(),
        "source_config": get_source_config_state(),
        "stored_source_config": state.get("source_config"),
    }


def get_readiness_status() -> dict[str, Any]:
    stats = get_stats() or {}
    schedule = get_research_schedule()
    delivery = get_delivery_summary(limit=3, max_chars=1200)
    source_config = get_source_config_state()

    total_documents = int(stats.get("total_documents") or 0)
    sources = source_config.get("sources") if isinstance(source_config.get("sources"), dict) else {}
    enabled_sources = [
        name for name, payload in sources.items()
        if isinstance(payload, dict) and payload.get("enabled")
    ]
    latest_brief_path = str(delivery.get("latest_brief_path") or "").strip()
    recent_topic_count = int(delivery.get("recent_topic_count") or 0)
    queue_count = len(list_queue_topics())

    checks = {
        "schedule_enabled": bool(schedule.get("enabled")),
        "source_enabled": bool(enabled_sources),
        "knowledge_index_available": total_documents > 0,
        "recent_brief_available": bool(latest_brief_path),
        "recent_history_available": recent_topic_count > 0,
    }
    all_ready = all(checks.values())
    blocking = [name for name, ok in checks.items() if not ok]
    return {
        "ready": all_ready,
        "checks": checks,
        "blocking": blocking,
        "summary": {
            "enabled_sources": enabled_sources,
            "total_documents": total_documents,
            "latest_brief_path": latest_brief_path or None,
            "recent_topic_count": recent_topic_count,
            "queue_count": queue_count,
        },
    }


def _db_path() -> Path | None:
    try:
        from hg_knowledge.config import get_config

        return get_config().get_database_path()
    except Exception:
        return None


def _shared_gateway_enabled() -> bool:
    import os

    return (os.environ.get("HG_GATEWAY_STORE") or "").strip().lower() in {"sqlite", "postgres"}


def _normalize_content_for_hash(text: str) -> bytes:
    """Normalize so same article with different dates/timestamps hashes the same."""
    if not text:
        return b""
    t = re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", text)
    t = re.sub(r"Accessed\s+DATE", "Accessed DATE", t, flags=re.IGNORECASE)
    t = re.sub(r"Last Updated:\s*[^\n]+", "Last Updated: DATE", t, flags=re.IGNORECASE)
    t = re.sub(r"Generated:\s*[^\n]+", "Generated: DATE", t, flags=re.IGNORECASE)
    t = re.sub(r"\d{8}T\d{6}Z", "TIMESTAMP", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip().encode("utf-8")


def _backfill_knowledge_file_hash(conn) -> None:
    """Set file_hash from normalized content so duplicate articles (different timestamps) collapse."""
    try:
        rows = conn.execute("SELECT file_path, content FROM knowledge_documents").fetchall()
        for r in rows:
            path = _row_value(r, "file_path")
            content = _row_value(r, "content") or ""
            if not path:
                continue
            normalized = _normalize_content_for_hash(content)
            h = hashlib.sha256(normalized).hexdigest() if normalized else ""
            conn.execute("UPDATE knowledge_documents SET file_hash = ? WHERE file_path = ?", (h, path))
    except Exception:
        pass


def run_dedupe_once() -> dict[str, Any]:
    """One-time: backfill file_hash, dedupe by hash, then by (title, category). Call once to remove duplicates."""
    if not _shared_gateway_enabled():
        return {"ok": False, "error": "shared gateway not enabled"}
    try:
        from hg_gateway.db import get_connection
        with get_connection() as conn:
            _backfill_knowledge_file_hash(conn)
            _dedupe_knowledge_by_hash(conn)
            _dedupe_knowledge_by_title_category(conn)
        return {"ok": True, "message": "duplicates removed from database"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _dedupe_knowledge_by_hash(conn) -> None:
    """Keep one row per file_hash (latest last_indexed). Postgres primary; reduces duplicate content."""
    try:
        rows = conn.execute(
            "SELECT file_path, file_hash, last_indexed FROM knowledge_documents WHERE file_hash IS NOT NULL AND file_hash != ''"
        ).fetchall()
        if not rows:
            return
        by_hash: dict[str, Any] = {}
        for r in rows:
            h = str(_row_value(r, "file_hash") or "").strip()
            if not h:
                continue
            prev = by_hash.get(h)
            cur_ts = str(_row_value(r, "last_indexed") or "")
            if prev is None or (cur_ts > str(_row_value(prev, "last_indexed") or "")):
                by_hash[h] = r
        keep_paths = {str(_row_value(r, "file_path") or "") for r in by_hash.values() if _row_value(r, "file_path")}
        for r in rows:
            path = str(_row_value(r, "file_path") or "")
            if path and path not in keep_paths:
                conn.execute("DELETE FROM knowledge_documents WHERE file_path = ?", (path,))
    except Exception:
        pass


def _dedupe_knowledge_by_title_category(conn) -> None:
    """Keep one row per (title, category), latest last_indexed. Collapses same-doc duplicates with different hashes."""
    try:
        rows = conn.execute(
            "SELECT file_path, title, category, last_indexed FROM knowledge_documents"
        ).fetchall()
        if not rows:
            return
        key = lambda r: (str(_row_value(r, "title") or "").strip(), str(_row_value(r, "category") or "").strip())
        by_key: dict[tuple[str, str], Any] = {}
        for r in rows:
            k = key(r)
            cur_ts = str(_row_value(r, "last_indexed") or "")
            prev = by_key.get(k)
            if prev is None or (cur_ts > str(_row_value(prev, "last_indexed") or "")):
                by_key[k] = r
        keep_paths = {str(_row_value(r, "file_path") or "") for r in by_key.values() if _row_value(r, "file_path")}
        for r in rows:
            path = str(_row_value(r, "file_path") or "")
            if path and path not in keep_paths:
                conn.execute("DELETE FROM knowledge_documents WHERE file_path = ?", (path,))
    except Exception:
        pass


def _shared_stats() -> dict[str, Any] | None:
    """Stats from shared gateway. Counts unique documents by (title, category) so duplicates don't inflate numbers."""
    if not _shared_gateway_enabled():
        return None
    try:
        from hg_gateway.db import get_connection

        # One row per (title, category) so stats reflect unique documents, not raw row count
        with get_connection() as conn:
            total_row = conn.execute(
                """
                SELECT COUNT(*) AS count FROM (
                    SELECT 1 FROM knowledge_documents
                    GROUP BY COALESCE(title,''), COALESCE(category,'')
                ) AS u
                """
            ).fetchone()
            total = int(_row_value(total_row, "count", 0) or 0)
            rows = conn.execute(
                """
                SELECT u.category, COUNT(*) AS doc_count
                FROM (
                    SELECT title, category FROM knowledge_documents
                    GROUP BY COALESCE(title,''), COALESCE(category,'')
                ) AS u
                GROUP BY u.category
                ORDER BY doc_count DESC
                """
            ).fetchall()
        return {
            "total_documents": total,
            "by_category": [{"category": _row_value(row, "category") or "(uncategorized)", "count": int(_row_value(row, "doc_count", 0) or 0)} for row in rows],
        }
    except Exception:
        return None


def _shared_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search shared knowledge; one result per content (dedupe by file_hash). Postgres primary."""
    if not _shared_gateway_enabled():
        return []
    try:
        from hg_gateway.db import get_connection

        q = (query or "").strip().lower()
        if not q:
            return []
        like = f"%{q}%"
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT file_path, title, category, language, content, file_hash
                FROM knowledge_documents
                WHERE lower(title) LIKE ? OR lower(content) LIKE ? OR lower(category) LIKE ?
                ORDER BY last_indexed DESC
                LIMIT ?
                """,
                (like, like, like, max(limit * 25, 200)),
            ).fetchall()
        out = []
        seen_hashes: set[str] = set()
        seen_title_category: set[tuple[str, str]] = set()
        for row in rows:
            title_key = (str(_row_value(row, "title") or "").strip(), str(_row_value(row, "category") or "").strip())
            if title_key in seen_title_category:
                continue
            seen_title_category.add(title_key)
            h = str(_row_value(row, "file_hash") or "").strip()
            if not h:
                content = _row_value(row, "content") or ""
                if content:
                    h = hashlib.sha256(content[:12000].encode("utf-8")).hexdigest()
            if h and h in seen_hashes:
                continue
            if h:
                seen_hashes.add(h)
            content = _row_value(row, "content") or ""
            lowered = content.lower()
            pos = lowered.find(q)
            if pos < 0:
                pos = 0
            start = max(0, pos - 48)
            end = min(len(content), pos + 160)
            snippet = content[start:end].strip()
            out.append(
                {
                    "file_path": _row_value(row, "file_path"),
                    "title": _row_value(row, "title"),
                    "category": _row_value(row, "category"),
                    "language": _row_value(row, "language"),
                    "snippet": snippet,
                    "rank": 0.0,
                }
            )
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def get_stats() -> dict[str, Any] | None:
    shared = _shared_stats()
    if shared is not None and int(shared.get("total_documents") or 0) > 0:
        return shared
    return None


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    shared = _shared_search(query, limit=limit)
    if shared:
        return shared
    return []


def read_document(*, file_path: str = "", title: str = "", max_chars: int = 4000) -> dict[str, Any] | None:
    document = _shared_read_document(file_path=file_path, title=title, max_chars=max_chars)
    if document is not None:
        return document
    return None


def get_delivery_summary(*, limit: int = 5, max_chars: int = 3000) -> dict[str, Any]:
    limit = max(1, min(int(limit or 5), 10))
    max_chars = max(400, min(int(max_chars or 3000), 8000))

    history_ref = f"db:knowledge:research_history:{RESEARCH_JOB_ID}"
    history_payload = load_research_history(RESEARCH_JOB_ID, limit=100)
    topics = history_payload.get("topics_researched") if isinstance(history_payload, dict) else []
    if not isinstance(topics, list):
        topics = []

    recent_topics: list[dict[str, Any]] = []
    latest_brief_source_mix: dict[str, int] | None = None
    for item in reversed(topics):
        if not isinstance(item, dict):
            continue
        current_source_mix = item.get("source_mix") if isinstance(item.get("source_mix"), dict) else None
        recent_topics.append(
            {
                "topic": str(item.get("topic") or "").strip(),
                "category": str(item.get("category") or "").strip() or None,
                "file_path": str(item.get("file_path") or "").strip() or None,
                "date": str(item.get("date") or item.get("last_research_date") or "").strip() or None,
                "requested_by": str(item.get("requested_by") or "").strip() or None,
                "priority": str(item.get("priority") or "").strip().lower() or None,
                "source_mix": current_source_mix or None,
            }
        )
        if latest_brief_source_mix is None and str(item.get("topic") or "").strip().lower() == "current events brief" and current_source_mix:
            latest_brief_source_mix = {str(key): int(value) for key, value in current_source_mix.items()}
        if len(recent_topics) >= limit:
            break

    brief_path: Path | None = None
    brief_preview = ""
    brief_files = sorted(_current_events_dir().glob("brief-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    if brief_files:
        brief_path = brief_files[0]
        try:
            brief_preview = brief_path.read_text(encoding="utf-8")[:max_chars].strip()
        except OSError:
            brief_preview = ""

    return {
        "history_path": history_ref,
        "recent_topics": recent_topics,
        "recent_topic_count": len(recent_topics),
        "latest_brief_path": str(brief_path) if brief_path is not None else None,
        "latest_brief_preview": brief_preview,
        "latest_brief_truncated": bool(brief_path is not None and len(brief_preview) >= max_chars),
        "latest_brief_source_mix": latest_brief_source_mix,
        "queue": list_queue_topics()[:limit],
    }


def get_categories() -> list[dict[str, Any]]:
    stats = get_stats()
    if stats is None:
        return []
    return stats.get("by_category", [])


def _shared_read_document(*, file_path: str = "", title: str = "", max_chars: int = 4000) -> dict[str, Any] | None:
    if not _shared_gateway_enabled():
        return None
    normalized_file_path = str(file_path or "").strip().replace("\\", "/")
    normalized_title = str(title or "").strip()
    if not normalized_file_path and not normalized_title:
        return None
    try:
        from hg_gateway.db import get_connection

        with get_connection() as conn:
            if normalized_file_path:
                row = conn.execute(
                    """
                    SELECT file_path, title, category, language, content, last_indexed
                    FROM knowledge_documents
                    WHERE file_path = ?
                    ORDER BY last_indexed DESC
                    LIMIT 1
                    """,
                    (normalized_file_path,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT file_path, title, category, language, content, last_indexed
                    FROM knowledge_documents
                    WHERE lower(title) = lower(?)
                    ORDER BY last_indexed DESC
                    LIMIT 1
                    """,
                    (normalized_title,),
                ).fetchone()
        if row is None:
            return None
        content = str(_row_value(row, "content") or "")
        clipped = content[: max(200, min(int(max_chars or 4000), 12000))]
        return {
            "file_path": _row_value(row, "file_path"),
            "title": _row_value(row, "title"),
            "category": _row_value(row, "category"),
            "language": _row_value(row, "language"),
            "content": clipped,
            "content_truncated": len(clipped) < len(content),
            "last_indexed": _row_value(row, "last_indexed"),
        }
    except Exception:
        return None
