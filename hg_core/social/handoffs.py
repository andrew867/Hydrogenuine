"""
Handoffs: HANDOFF_CREATED, HANDOFF_ACCEPTED, HANDOFF_REJECTED, HANDOFF_COMPLETED.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit
from .artifacts import write_handoff_notes


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_handoff(
    *,
    from_agent_id: str,
    to_agent_id: str,
    work_item_ref: Dict[str, Any],
    ownership_mode: str,
    expected_response_by: str,
    priority: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    ultimate_owner_agent_id: Optional[str] = None,
    notes: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit HANDOFF_CREATED. ownership_mode: own|delegate|collaborate|review; priority: low|normal|high|urgent. Returns handoff_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    wid = work_item_ref.get("id", "")
    handoff_id = hashlib.sha256(f"{from_agent_id}:{to_agent_id}:{wid}:{ts}".encode()).hexdigest()
    notes_artifact_id = handoff_id
    if notes:
        write_handoff_notes(workspace_root, handoff_id, {"handoff_id": handoff_id, "notes": notes, "ts": ts, "work_item_id": wid})
    if ownership_mode not in ("own", "delegate", "collaborate", "review"):
        ownership_mode = "delegate"
    if priority not in ("low", "normal", "high", "urgent"):
        priority = "normal"
    emit(
        "HANDOFF_CREATED",
        "handoff",
        handoff_id,
        {
            "handoff_id": handoff_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "work_item_ref": work_item_ref,
            "ownership_mode": ownership_mode,
            "ultimate_owner_agent_id": ultimate_owner_agent_id or "",
            "expected_response_by": expected_response_by,
            "priority": priority,
            "notes_artifact_id": notes_artifact_id,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return handoff_id


def accept_handoff(
    handoff_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit HANDOFF_ACCEPTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "HANDOFF_ACCEPTED",
        "handoff",
        handoff_id,
        {"handoff_id": handoff_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def reject_handoff(
    handoff_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit HANDOFF_REJECTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "HANDOFF_REJECTED",
        "handoff",
        handoff_id,
        {"handoff_id": handoff_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def complete_handoff(
    handoff_id: str,
    outcome: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit HANDOFF_COMPLETED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "HANDOFF_COMPLETED",
        "handoff",
        handoff_id,
        {"handoff_id": handoff_id, "outcome": outcome, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
