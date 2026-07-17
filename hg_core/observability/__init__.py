"""
OS Phase 3: Observability — metrics, SLOs, trace_id, alerts, and decision-context logging.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .metrics import (
    get_metrics,
    record_ledger_append,
    record_materializer_run,
    record_sandbox_run,
    record_stream_connection,
    record_stream_lag,
    record_stream_dropped,
    record_api_request,
    record_control_action,
    format_openmetrics,
)
from .slo import load_slo_config, check_slos
from .trace import get_trace_id, set_trace_id

try:  # lightweight fallback mirroring hg_core/observability.py
    from hg_lib.config import get_workspace_root  # type: ignore
except ImportError:  # pragma: no cover
    def get_workspace_root() -> Path:  # type: ignore[override]
        return Path(".")


def get_run_id() -> str:
    """Return a new run identifier (12-character hex string)."""
    return uuid.uuid4().hex[:12]


def _get_decision_log_path(workspace_root: Optional[Path] = None) -> Path:
    """Path to global decision log (JSONL)."""
    root = workspace_root if workspace_root is not None else get_workspace_root()
    return root / "memory" / "overseer" / "decision_log.jsonl"


def log_decision(
    agent_id: str,
    key: str,
    value: Any,
    run_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> None:
    """
    Log a key choice point for the current run (decision-context hook).

    Appends one JSONL line to memory/overseer/decision_log.jsonl with
    entity_id, run_id, timestamp, event_type="decision", payload={"key": key, "value": value}.
    """
    root = workspace_root if workspace_root is not None else get_workspace_root()
    log_path = _get_decision_log_path(root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "entity_id": agent_id,
        "run_id": run_id or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "decision",
        "payload": {"key": key, "value": value},
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except (OSError, TypeError):  # pragma: no cover - logging failure shouldn't crash
        pass


__all__ = [
    "get_metrics",
    "record_ledger_append",
    "record_materializer_run",
    "record_sandbox_run",
    "record_stream_connection",
    "record_stream_lag",
    "record_stream_dropped",
    "record_api_request",
    "record_control_action",
    "format_openmetrics",
    "load_slo_config",
    "check_slos",
    "get_trace_id",
    "set_trace_id",
    "get_run_id",
    "log_decision",
]
