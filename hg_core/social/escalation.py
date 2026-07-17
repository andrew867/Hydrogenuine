"""Escalation and conflict: ESCALATION_RAISED, CONFLICT_DETECTED."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def raise_escalation(
    *,
    handoff_id: Optional[str] = None,
    work_item_ref: Optional[Dict[str, Any]] = None,
    reason: str,
    to_agent_id: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ESCALATION_RAISED (e.g. missed deadline, to_agent unavailable). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload: Dict[str, Any] = {"reason": reason, "ts": ts}
    if handoff_id:
        payload["handoff_id"] = handoff_id
    if work_item_ref:
        payload["work_item_ref"] = work_item_ref
    if to_agent_id:
        payload["to_agent_id"] = to_agent_id
    esc_id = f"esc_{ts.replace(':', '-')}"
    return emit(
        "ESCALATION_RAISED",
        "escalation",
        esc_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_conflict(
    *,
    work_item_ref: Dict[str, Any],
    agent_ids: List[str],
    trace: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit CONFLICT_DETECTED when two agents claim ownership on same work item. Does not silently resolve; explicit resolution event required. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    conflict_id = f"conflict_{work_item_ref.get('id', '')}_{ts.replace(':', '-')}"[:64]
    return emit(
        "CONFLICT_DETECTED",
        "conflict",
        conflict_id,
        {"work_item_ref": work_item_ref, "agent_ids": agent_ids, "trace": trace, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
