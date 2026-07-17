"""
Per-task posting dedupe: prevent double post on retry.

Dedupe key = (task_id, date_bucket, content_hash). When the same run retries
(same task, same date, same content), we return the existing post result instead
of posting again. See token_optimization_and_autonomy_plumbing plan a1.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEDUPE_FILE = "post_dedupe.json"
MAX_AGE_DAYS = 7
MAX_KEYS = 500


def get_date_bucket() -> str:
    """UTC date bucket YYYY-MM-DD for dedupe key."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def make_dedupe_key(task_id: str, date_bucket: str, content_hash: str) -> str:
    """Build dedupe key: task_id:date_bucket:content_hash."""
    return f"{task_id}:{date_bucket}:{content_hash}"


def _dedupe_path(workspace: Path, session_target: str) -> Path:
    """Path to per-session post_dedupe.json."""
    return workspace / "memory" / "automation" / session_target / DEDUPE_FILE


def _load_dedupe(workspace: Path, session_target: str) -> Dict[str, Any]:
    path = _dedupe_path(workspace, session_target)
    if not path.exists():
        return {"keys": {}, "by_date": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"keys": {}, "by_date": {}}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load post_dedupe %s: %s", path, e)
        return {"keys": {}, "by_date": {}}


def _prune(data: Dict[str, Any]) -> None:
    """Keep only keys from last MAX_AGE_DAYS and cap total."""
    keys = data.get("keys") or {}
    by_date = data.get("by_date") or {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")
    to_drop = []
    for key, meta in list(keys.items()):
        at = meta.get("at", "")[:10]
        if at < cutoff:
            to_drop.append(key)
    for k in to_drop:
        keys.pop(k, None)
    for d in list(by_date.keys()):
        if d < cutoff:
            by_date.pop(d, None)
    # Cap total
    if len(keys) > MAX_KEYS:
        by_key = sorted(keys.items(), key=lambda x: x[1].get("at", ""))
        for k, _ in by_key[: len(keys) - MAX_KEYS]:
            keys.pop(k, None)
    data["keys"] = keys
    data["by_date"] = by_date


def _save_dedupe(workspace: Path, session_target: str, data: Dict[str, Any]) -> None:
    path = _dedupe_path(workspace, session_target)
    path.parent.mkdir(parents=True, exist_ok=True)
    _prune(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.warning("Could not save post_dedupe %s: %s", path, e)


def check_already_posted(
    workspace: Path,
    session_target: str,
    task_id: str,
    date_bucket: str,
    content_hash: str,
) -> Optional[Dict[str, Any]]:
    """
    Return existing post result if this (task, date, content) was already posted; else None.
    Call before posting; if not None, return this result and do not post again (idempotent).
    """
    key = make_dedupe_key(task_id, date_bucket, content_hash)
    data = _load_dedupe(workspace, session_target)
    keys = data.get("keys") or {}
    entry = keys.get(key)
    if not entry or not isinstance(entry, dict):
        return None
    thread_id = entry.get("thread_id")
    thread_url = entry.get("thread_url")
    if thread_id or thread_url:
        return {"thread_id": thread_id, "thread_url": thread_url, "at": entry.get("at")}
    return None


def record_posted(
    workspace: Path,
    session_target: str,
    task_id: str,
    date_bucket: str,
    content_hash: str,
    thread_id: Optional[str] = None,
    thread_url: Optional[str] = None,
) -> None:
    """Record a successful post so retries return this result instead of posting again."""
    key = make_dedupe_key(task_id, date_bucket, content_hash)
    data = _load_dedupe(workspace, session_target)
    keys = data.get("keys") or {}
    by_date = data.get("by_date") or {}
    at = datetime.now(timezone.utc).isoformat()
    keys[key] = {"thread_id": thread_id, "thread_url": thread_url, "at": at}
    by_date.setdefault(date_bucket, []).append(key)
    data["keys"] = keys
    data["by_date"] = by_date
    _save_dedupe(workspace, session_target, data)
