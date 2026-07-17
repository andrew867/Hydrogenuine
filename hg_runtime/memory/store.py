"""RTC bounded memory index — file-backed, per runtime_dir, no GC/prune logic."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.contract import stable_id
from hg_runtime.memory.types import redact_mapping

MAX_SUMMARIES = 32
INDEX_VERSION = 1


def memory_enabled() -> bool:
    raw = os.environ.get("HG_RTC_MEMORY_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no")


def index_path(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "rtc_memory_index.json"


def load_index(runtime_dir: Path) -> dict[str, Any]:
    path = index_path(runtime_dir)
    if not path.exists():
        return {"version": INDEX_VERSION, "summaries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": INDEX_VERSION, "summaries": []}
    if not isinstance(data, dict):
        return {"version": INDEX_VERSION, "summaries": []}
    summaries = data.get("summaries", [])
    if not isinstance(summaries, list):
        summaries = []
    return {"version": INDEX_VERSION, "summaries": summaries[-MAX_SUMMARIES:]}


def save_index(runtime_dir: Path, index: Mapping[str, Any]) -> None:
    path = index_path(runtime_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    summaries = list(index.get("summaries", []))[-MAX_SUMMARIES:]
    payload = {"version": INDEX_VERSION, "summaries": summaries}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def append_tick_summary(
    runtime_dir: Path,
    *,
    summary: Mapping[str, Any],
    event_refs: tuple[str, ...],
) -> str:
    index = load_index(runtime_dir)
    memory_ref = stable_id("rtc_mem", *event_refs[:8]) if event_refs else stable_id("rtc_mem", "empty")
    entry = {
        "memory_ref": memory_ref,
        "summary": redact_mapping(dict(summary)),
        "event_refs": list(event_refs[:64]),
    }
    summaries = list(index.get("summaries", []))
    summaries.append(entry)
    save_index(runtime_dir, {"summaries": summaries})
    return memory_ref


def retrieve_summaries(runtime_dir: Path, *, limit: int = 8) -> list[dict[str, Any]]:
    index = load_index(runtime_dir)
    summaries = index.get("summaries", [])
    if not isinstance(summaries, list):
        return []
    return [dict(row) for row in summaries[-limit:] if isinstance(row, dict)]


def load_session_context(session_id: str, *, max_tokens: int) -> dict[str, Any] | None:
    """Optional: reuse hg_core.session_manager compacted memory (read-only)."""
    try:
        from hg_core.session_manager import load_compacted_memory

        memory = load_compacted_memory(session_id, max_tokens=max_tokens)
        return redact_mapping(memory) if isinstance(memory, dict) else None
    except Exception:
        return None


__all__ = [
    "append_tick_summary",
    "index_path",
    "load_index",
    "load_session_context",
    "memory_enabled",
    "retrieve_summaries",
    "save_index",
]
