"""
Behavior telemetry schema and validation (Autonomy Ch5).

Emit and validate behavior events per docs/specs/behavior_telemetry_schema.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = frozenset({
    "timestamp", "run_id", "workflow_id", "work_item_id", "agent_id",
    "event_type", "payload_summary", "pointers", "severity",
})
VALID_EVENT_TYPES = frozenset({
    "delegation.assign", "delegation.handoff", "delegation.split", "delegation.merge",
    "delegation.escalate", "decision.point", "safety.blocked", "budget.exceeded",
    "loop.detected", "anomaly.flagged",
})
VALID_SEVERITIES = frozenset({"info", "warn", "critical"})


def validate_behavior_event(payload: Dict[str, Any]) -> List[str]:
    """Validate a behavior event against schema. Returns list of error strings (empty if valid)."""
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")
    if payload.get("event_type") and payload["event_type"] not in VALID_EVENT_TYPES:
        errors.append(f"invalid event_type: {payload['event_type']}")
    if payload.get("severity") and payload["severity"] not in VALID_SEVERITIES:
        errors.append(f"invalid severity: {payload['severity']}")
    return errors


def make_behavior_event(
    run_id: str,
    workflow_id: str,
    work_item_id: str,
    event_type: str,
    agent_id: str = "",
    parent_work_item_id: Optional[str] = None,
    payload_summary: Optional[Dict[str, Any]] = None,
    pointers: Optional[List[str]] = None,
    severity: str = "info",
) -> Dict[str, Any]:
    """Build a valid behavior event dict (with timestamp)."""
    payload_summary = payload_summary or {}
    pointers = pointers or []
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "workflow_id": workflow_id,
        "work_item_id": work_item_id,
        "agent_id": agent_id,
        "event_type": event_type,
        "payload_summary": payload_summary,
        "pointers": pointers,
        "severity": severity,
    }
    if parent_work_item_id is not None:
        event["parent_work_item_id"] = parent_work_item_id
    return event


def emit_behavior_event(
    run_dir: Path,
    event: Dict[str, Any],
    behavior_events_path: Optional[Path] = None,
) -> None:
    """Append one behavior event to run_dir/behavior_events.jsonl. Optionally merge into events.jsonl."""
    path = behavior_events_path or (run_dir / "behavior_events.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    errs = validate_behavior_event(event)
    if errs:
        raise ValueError(f"invalid behavior event: {errs}")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
        f.flush()
