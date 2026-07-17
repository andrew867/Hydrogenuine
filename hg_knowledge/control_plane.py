from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from hg_gateway.shared_storage import get_operational_state, put_operational_state

DEFAULT_SOURCE_CONFIG: dict[str, Any] = {
    "brave": {"enabled": True, "news_count": 4, "web_count": 5},
    "google_news": {"enabled": False, "news_count": 4, "hl": "en-US", "gl": "US", "ceid": "US:en"},
    "local_news": {"enabled": False, "urls": [], "timeout_s": 8},
}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_config_key() -> str:
    return "knowledge:source_config"


def _queue_key() -> str:
    return "knowledge:research_queue"


def _history_key(task_name: str) -> str:
    return f"knowledge:research_history:{str(task_name or '').strip() or 'default'}"


def _merge_source_config(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "brave": dict(DEFAULT_SOURCE_CONFIG["brave"]),
        "google_news": dict(DEFAULT_SOURCE_CONFIG["google_news"]),
        "local_news": dict(DEFAULT_SOURCE_CONFIG["local_news"]),
    }
    for key in ("brave", "google_news", "local_news"):
        if isinstance(current.get(key), dict):
            merged[key].update(current[key])

    brave_in = incoming.get("brave") if isinstance(incoming.get("brave"), dict) else {}
    google_in = incoming.get("google_news") if isinstance(incoming.get("google_news"), dict) else {}
    local_in = incoming.get("local_news") if isinstance(incoming.get("local_news"), dict) else {}

    merged["brave"]["enabled"] = bool(brave_in.get("enabled", merged["brave"].get("enabled", True)))
    merged["brave"]["news_count"] = max(1, min(int(brave_in.get("news_count") or merged["brave"].get("news_count") or 4), 25))
    merged["brave"]["web_count"] = max(1, min(int(brave_in.get("web_count") or merged["brave"].get("web_count") or 5), 25))

    merged["google_news"]["enabled"] = bool(google_in.get("enabled", merged["google_news"].get("enabled", False)))
    merged["google_news"]["news_count"] = max(1, min(int(google_in.get("news_count") or merged["google_news"].get("news_count") or 4), 25))
    merged["google_news"]["hl"] = str(google_in.get("hl") or merged["google_news"].get("hl") or "en-US").strip() or "en-US"
    merged["google_news"]["gl"] = str(google_in.get("gl") or merged["google_news"].get("gl") or "US").strip() or "US"
    merged["google_news"]["ceid"] = str(google_in.get("ceid") or merged["google_news"].get("ceid") or "US:en").strip() or "US:en"
    merged["google_news"]["timeout_s"] = max(2, min(int(google_in.get("timeout_s") or merged["google_news"].get("timeout_s") or 8), 60))

    merged["local_news"]["enabled"] = bool(local_in.get("enabled", merged["local_news"].get("enabled", False)))
    urls = local_in.get("urls") if isinstance(local_in.get("urls"), list) else merged["local_news"].get("urls") or []
    merged["local_news"]["urls"] = [str(item).strip() for item in urls if str(item).strip()]
    merged["local_news"]["timeout_s"] = max(2, min(int(local_in.get("timeout_s") or merged["local_news"].get("timeout_s") or 8), 60))
    return merged


def load_source_config() -> dict[str, Any]:
    payload = get_operational_state(_source_config_key(), None)
    if not isinstance(payload, dict):
        return {
            "brave": dict(DEFAULT_SOURCE_CONFIG["brave"]),
            "google_news": dict(DEFAULT_SOURCE_CONFIG["google_news"]),
            "local_news": dict(DEFAULT_SOURCE_CONFIG["local_news"]),
        }
    return _merge_source_config(DEFAULT_SOURCE_CONFIG, payload)


def save_source_config(sources: dict[str, Any]) -> dict[str, Any]:
    current = load_source_config()
    merged = _merge_source_config(current, sources if isinstance(sources, dict) else {})
    put_operational_state(_source_config_key(), merged)
    return merged


def list_queue_topics() -> list[dict[str, Any]]:
    payload = get_operational_state(_queue_key(), {"queued_topics": []})
    queued = payload.get("queued_topics") if isinstance(payload, dict) else []
    if not isinstance(queued, list):
        return []
    out: list[dict[str, Any]] = []
    for item in queued:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        out.append(
            {
                "topic": topic,
                "requested_by": str(item.get("requested_by") or "").strip(),
                "priority": str(item.get("priority") or "medium").strip().lower() or "medium",
                "context": str(item.get("context") or item.get("reason") or "").strip(),
                "date_requested": str(item.get("date_requested") or item.get("queued_at") or "").strip() or None,
            }
        )
    return out


def queue_topic(topic: str, *, requested_by: str = "", priority: str = "medium", context: str = "") -> dict[str, Any]:
    normalized_topic = str(topic or "").strip()
    if not normalized_topic:
        raise ValueError("topic is required")
    existing = list_queue_topics()
    key = normalized_topic.lower()
    if not any(str(item.get("topic") or "").strip().lower() == key for item in existing):
        existing.append(
            {
                "topic": normalized_topic,
                "requested_by": str(requested_by or "").strip(),
                "priority": str(priority or "medium").strip().lower() or "medium",
                "context": str(context or "").strip()[:400],
                "date_requested": _now(),
            }
        )
        put_operational_state(_queue_key(), {"queued_topics": existing[-150:]})
    return {"ok": True, "queued_topics": list_queue_topics(), "queue_count": len(list_queue_topics())}


def remove_queue_topic(topic: str) -> dict[str, Any]:
    normalized = str(topic or "").strip().lower()
    existing = list_queue_topics()
    updated = [item for item in existing if str(item.get("topic") or "").strip().lower() != normalized]
    put_operational_state(_queue_key(), {"queued_topics": updated})
    return {"ok": True, "removed": len(existing) - len(updated), "queued_topics": updated, "queue_count": len(updated)}


def clear_queue_topics() -> dict[str, Any]:
    put_operational_state(_queue_key(), {"queued_topics": []})
    return {"ok": True, "removed": "all", "queued_topics": [], "queue_count": 0}


def list_research_history(task_name: str, *, limit: int = 100) -> dict[str, Any]:
    payload = get_operational_state(_history_key(task_name), {"topics_researched": [], "last_research_date": None, "total_topics": 0})
    if not isinstance(payload, dict):
        payload = {"topics_researched": [], "last_research_date": None, "total_topics": 0}
    topics = payload.get("topics_researched")
    if not isinstance(topics, list):
        topics = []
    normalized = [item for item in topics if isinstance(item, dict)]
    payload["topics_researched"] = normalized[-max(1, min(int(limit or 100), 200)) :]
    payload["last_research_date"] = str(payload.get("last_research_date") or "").strip() or None
    payload["total_topics"] = int(payload.get("total_topics") or len(normalized))
    return payload


def load_research_history(task_name: str, *, limit: int = 100) -> dict[str, Any]:
    return list_research_history(task_name, limit=limit)


def append_research_history(
    task_name: str,
    *,
    topic: str,
    file_path: str,
    source_count: int,
    source_mix: dict[str, int] | None = None,
) -> str:
    payload = list_research_history(task_name, limit=1000)
    topics = payload.get("topics_researched")
    if not isinstance(topics, list):
        topics = []
    entry: dict[str, Any] = {
        "topic": str(topic or "").strip(),
        "file_path": str(file_path or "").strip(),
        "date": _now().split("T", 1)[0],
        "source_count": int(source_count or 0),
    }
    if isinstance(source_mix, dict) and source_mix:
        entry["source_mix"] = {str(key): int(value) for key, value in source_mix.items()}
    topics.append(entry)
    payload["topics_researched"] = topics[-100:]
    payload["last_research_date"] = _now()
    payload["total_topics"] = len(payload["topics_researched"])
    put_operational_state(_history_key(task_name), payload)
    return f"db:{_history_key(task_name)}"


def get_control_plane_state() -> dict[str, Any]:
    queue = list_queue_topics()
    return {
        "queue_count": len(queue),
        "queued_topics": queue,
        "source_config": load_source_config(),
    }
