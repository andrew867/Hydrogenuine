"""
Observability: run IDs, decision-context log hook, structured execution log.
See docs/specs/observability_spec.md.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from hg_lib.config import get_workspace_root
except ImportError:
    def get_workspace_root() -> Path:
        return Path(".")


def get_run_id() -> str:
    """Return a new run identifier (short hex) for the current execution."""
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
    except (OSError, TypeError):
        pass
