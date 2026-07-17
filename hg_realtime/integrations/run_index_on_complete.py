"""Update run index on completion (Phase 9). Call from run_dag_job or after executor.run().
Uses the same store as the realtime worker (gateway DB) when db_path is None so runs are never split across DBs."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _parse_completed_ts(value: Any) -> float:
    """Normalize summary ended_at to epoch seconds (handles ISO strings and numeric timestamps)."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return time.time()
        try:
            return float(text)
        except ValueError:
            pass
        try:
            normalized = text.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp()
        except ValueError:
            return time.time()
    return time.time()


def read_run_completion_from_summary(run_dir: Path | str) -> tuple[Optional[str], float]:
    """Read final_status and ended_at from summary.json. Returns (status, completed_ts)."""
    run_dir = Path(run_dir)
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return None, time.time()
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, time.time()
    if not isinstance(summary, dict):
        return None, time.time()
    final_status = summary.get("final_status") or summary.get("status")
    ended_at = summary.get("ended_at")
    completed_ts = _parse_completed_ts(ended_at) if ended_at is not None else time.time()
    return (str(final_status) if final_status else None), completed_ts


def update_run_index_on_complete(
    run_dir: Path,
    run_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """
    Read summary.json from run_dir, then update run index with final_status and ended_at.
    run_id: if None, use run_dir.name.
    db_path: If None, use gateway DB (same as worker). If set, use that SQLite path (legacy only).
    No-op if summary.json missing or update fails.
    """
    run_dir = Path(run_dir)
    rid = run_id or run_dir.name
    if not rid:
        return
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    final_status = summary.get("final_status") or summary.get("status") or "completed"
    _, completed_ts = read_run_completion_from_summary(run_dir)
    try:
        from .run_index import default_run_index_writer
        writer = default_run_index_writer(sqlite_path=db_path)
        writer.record_completion(run_id=rid, status=final_status, completed_ts=completed_ts)
    except Exception:
        pass
