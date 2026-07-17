"""
Workspace-based run summary log for human-notification ingest.

When the task-graph executor completes a DAG run (in-process), it appends one
record to memory/automation/run_summaries.jsonl. The overseer's cron_summary_ingest
reads this file in addition to ~/.hg/cron/runs so that both cron and in-process
runs feed the same human-notification pending queue.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


RUN_SUMMARIES_FILENAME = "run_summaries.jsonl"
MAX_LINES_READ = 1000


def _run_summaries_path(workspace_root: Path) -> Path:
    return workspace_root / "memory" / "automation" / RUN_SUMMARIES_FILENAME


def append_run_summary(
    workspace_root: Path,
    job_id: str,
    session_target: str,
    summary: str,
    status: str = "ok",
    run_id: Optional[str] = None,
) -> None:
    """Append one run summary record to run_summaries.jsonl."""
    path = _run_summaries_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts_ms = int(time.time() * 1000)
    record: Dict[str, Any] = {
        "job_id": job_id,
        "session_target": session_target,
        "summary": summary,
        "ts_ms": ts_ms,
        "status": status,
    }
    if run_id:
        record["run_id"] = run_id
    line = json.dumps(record, ensure_ascii=False) + "\n"
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def read_latest_per_job(workspace_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Read run_summaries.jsonl and return the latest record per job_id (by ts_ms).
    Returns dict mapping job_id -> {session_target, summary, ts_ms, status, run_id?}.
    """
    path = _run_summaries_path(workspace_root)
    if not path.exists():
        return {}
    latest: Dict[str, Dict[str, Any]] = {}
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return {}
    # Take last N lines to avoid reading huge files
    for raw in lines[-MAX_LINES_READ:]:
        raw = raw.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        job_id = record.get("job_id")
        if not job_id:
            continue
        ts_ms = int(record.get("ts_ms") or 0)
        if job_id not in latest or ts_ms > int(latest[job_id].get("ts_ms") or 0):
            latest[job_id] = {
                "session_target": record.get("session_target") or f"automation-{job_id}",
                "summary": record.get("summary") or "",
                "ts_ms": ts_ms,
                "status": str(record.get("status") or "ok"),
                "run_id": record.get("run_id"),
            }
    return latest
