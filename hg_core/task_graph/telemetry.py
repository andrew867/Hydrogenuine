"""
DAG executor telemetry: default sink writing events to JSONL.

Uses workspace root for path (memory/automation/dag_runs/events.jsonl).
When overseer is available, also calls OverseerLogger.log_dag_event.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional


def _default_events_dir() -> Path:
    """Default directory for DAG telemetry JSONL under workspace root."""
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root() / "memory" / "automation" / "dag_runs"
    except Exception:
        return Path("memory/automation/dag_runs")


def default_telemetry_sink(
    base_dir: Optional[Path] = None,
    overseer: Optional[Any] = None,
) -> Callable[[str, Dict[str, Any]], None]:
    """
    Return a telemetry callback that:
    1) Appends each event to base_dir/events.jsonl (or default under workspace).
    2) If overseer has log_dag_event, calls overseer.log_dag_event(event_name, payload).

    Use as TaskGraphExecutor(telemetry=default_telemetry_sink(overseer=...)) when
    telemetry is None the executor will use this with overseer=None unless you pass it.
    """
    dir_path = Path(base_dir) if base_dir is not None else _default_events_dir()

    def sink(event_name: str, payload: Dict[str, Any]) -> None:
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / "events.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event_name,
            **payload,
        }
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
        if overseer is not None and hasattr(overseer, "log_dag_event"):
            try:
                overseer.log_dag_event(event_name, payload)
            except Exception:
                pass

    return sink
