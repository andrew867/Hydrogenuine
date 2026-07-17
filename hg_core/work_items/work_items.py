"""
WorkItem lifecycle: create, update, assign, block/unblock, close, link.
Emits WORK_ITEM_* events via ledger; optional note artifacts for updates.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_update_note


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


VALID_WI_TYPES = ("task", "decision", "incident", "investigation", "change")
VALID_PRIORITIES = ("low", "normal", "high", "urgent")
VALID_STATUSES = ("proposed", "active", "blocked", "waiting_approval", "done", "abandoned")


def create_work_item(
    *,
    wi_type: str,
    title: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    description: str = "",
    priority: str = "normal",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_CREATED. wi_type: task|decision|incident|investigation|change. Returns work_item_id."""
    workspace_root = Path(workspace_root or ".")
    if wi_type not in VALID_WI_TYPES:
        raise ValueError(f"wi_type must be one of {VALID_WI_TYPES}")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
    ts = _iso_ts()
    work_item_id = "wi_" + hashlib.sha256(f"{wi_type}:{title}:{ts}".encode()).hexdigest()[:16]
    payload = {
        "work_item_id": work_item_id,
        "type": wi_type,
        "title": title,
        "description": description,
        "scope": scope,
        "created_ts": ts,
        "priority": priority,
        "status": "proposed",
    }
    emit(
        "WORK_ITEM_CREATED",
        "work_item",
        work_item_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return work_item_id


def update_work_item(
    *,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    changes: Dict[str, Any],
    note: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_UPDATED. Optionally write note artifact. Returns event object id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    upd_id = "upd_" + hashlib.sha256(f"{work_item_id}:{ts}".encode()).hexdigest()[:16]
    note_artifact_id = ""
    if note or changes:
        write_update_note(workspace_root, work_item_id, upd_id, {"note": note, "changes": changes, "ts": ts})
        note_artifact_id = upd_id
    payload = {"work_item_id": work_item_id, "ts": ts, "changes": changes}
    if note_artifact_id:
        payload["note_artifact_id"] = note_artifact_id
    return emit(
        "WORK_ITEM_UPDATED",
        "work_item_update",
        upd_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def assign_work_item(
    *,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    owner_agent_id: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_ASSIGNED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"work_item_id": work_item_id, "owner_agent_id": owner_agent_id, "ts": ts}
    return emit(
        "WORK_ITEM_ASSIGNED",
        "work_item",
        work_item_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def block_work_item(
    *,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_BLOCKED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"work_item_id": work_item_id, "reason": reason, "ts": ts}
    return emit(
        "WORK_ITEM_BLOCKED",
        "work_item",
        work_item_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def unblock_work_item(
    *,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_UNBLOCKED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"work_item_id": work_item_id, "ts": ts}
    return emit(
        "WORK_ITEM_UNBLOCKED",
        "work_item",
        work_item_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def close_work_item(
    *,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    status: str = "done",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_CLOSED. status: done|abandoned."""
    workspace_root = Path(workspace_root or ".")
    if status not in ("done", "abandoned"):
        raise ValueError("status must be done or abandoned")
    ts = _iso_ts()
    payload = {"work_item_id": work_item_id, "status": status, "ts": ts}
    return emit(
        "WORK_ITEM_CLOSED",
        "work_item",
        work_item_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def link_work_item(
    *,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    link_type: str,
    target_ref: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_LINKED. target_ref e.g. {type: decision, id: dec_1}."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    link_id = "lnk_" + hashlib.sha256(f"{work_item_id}:{link_type}:{ts}".encode()).hexdigest()[:16]
    payload = {"work_item_id": work_item_id, "link_type": link_type, "target_ref": target_ref, "ts": ts}
    return emit(
        "WORK_ITEM_LINKED",
        "work_item_link",
        link_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
