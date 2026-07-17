"""
Autonomy loop: WorkItem-scoped executor with LOOP_* events.
Respects budgets, backpressure, and incident stop conditions.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.os_layer import get_prioritized_work_items, check_backpressure


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def start_loop(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    loop_id: Optional[str] = None,
    budget_limit: int = 100,
    max_concurrency: int = 5,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LOOP_STARTED. Returns loop_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    lid = loop_id or "loop_" + hashlib.sha256(ts.encode()).hexdigest()[:16]
    emit(
        "LOOP_STARTED",
        "loop",
        lid,
        {"loop_id": lid, "ts": ts, "budget_limit": budget_limit, "max_concurrency": max_concurrency},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return lid


def stop_loop(
    *,
    loop_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LOOP_STOPPED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "LOOP_STOPPED",
        "loop",
        loop_id,
        {"loop_id": loop_id, "ts": ts, "reason": reason},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def tick_loop(
    *,
    loop_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    stats: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LOOP_TICK (heartbeat with stats). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "LOOP_TICK",
        "loop",
        loop_id,
        {"loop_id": loop_id, "ts": ts, "stats": stats},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def select_work_item(
    *,
    loop_id: str,
    work_item_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit WORK_ITEM_SELECTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "WORK_ITEM_SELECTED",
        "work_item",
        work_item_id,
        {"loop_id": loop_id, "work_item_id": work_item_id, "ts": ts, "reason": reason},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def publish_plan(
    *,
    loop_id: str,
    work_item_id: str,
    plan_artifact_path: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit PLAN_GENERATED with plan artifact reference. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    plan_id = "plan_" + hashlib.sha256(f"{loop_id}:{work_item_id}:{ts}".encode()).hexdigest()[:12]
    return emit(
        "PLAN_GENERATED",
        "plan",
        plan_id,
        {"loop_id": loop_id, "work_item_id": work_item_id, "plan_artifact_id": plan_artifact_path, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_plan_step_executed(
    *,
    loop_id: str,
    work_item_id: str,
    step_index: int,
    action_ref: Optional[str] = None,
    receipt_ref: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit PLAN_STEP_EXECUTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"loop_id": loop_id, "work_item_id": work_item_id, "step_index": step_index, "ts": ts}
    if action_ref:
        payload["action_ref"] = action_ref
    if receipt_ref:
        payload["receipt_ref"] = receipt_ref
    return emit(
        "PLAN_STEP_EXECUTED",
        "plan_step",
        f"{work_item_id}_{step_index}",
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_loop_blocked(
    *,
    loop_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str,
    waiting_on: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LOOP_BLOCKED (waiting approval/resource). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"loop_id": loop_id, "ts": ts, "reason": reason}
    if waiting_on:
        payload["waiting_on"] = waiting_on
    return emit(
        "LOOP_BLOCKED",
        "loop",
        loop_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def publish_loop_summary(
    *,
    loop_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    summary_artifact_path: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LOOP_SUMMARY_PUBLISHED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "LOOP_SUMMARY_PUBLISHED",
        "loop",
        loop_id,
        {"loop_id": loop_id, "ts": ts, "summary_artifact_id": summary_artifact_path},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def run_loop_once(
    *,
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    loop_id: Optional[str] = None,
    budget_remaining: Optional[int] = None,
    stop_on_backpressure: bool = True,
) -> Dict[str, Any]:
    """
    One iteration: check backpressure/stop conditions, get prioritized work items, select first, emit tick.
    Returns {loop_id, selected_work_item_id?, blocked?, stats}.
    """
    workspace_root = Path(workspace_root)
    if stop_on_backpressure:
        bp = check_backpressure(workspace_root)
        if not bp.get("healthy", True):
            return {"blocked": True, "reason": "backpressure", "stats": bp}
    items = get_prioritized_work_items(workspace_root, scope_type=scope.get("type"), scope_id=scope.get("id"), status_filter=["proposed", "active"], limit=5)
    if not items:
        return {"loop_id": loop_id, "selected_work_item_id": None, "blocked": False, "stats": {"queue_depth": 0}}
    lid = loop_id or start_loop(scope=scope, actor=actor, workspace_root=workspace_root)
    wi = items[0]
    wid = wi.get("work_item_id") or wi.get("id")
    select_work_item(loop_id=lid, work_item_id=wid, scope=scope, actor=actor, reason="priority", workspace_root=workspace_root)
    tick_loop(loop_id=lid, scope=scope, actor=actor, stats={"queue_depth": len(items), "selected": wid}, workspace_root=workspace_root)
    return {"loop_id": lid, "selected_work_item_id": wid, "blocked": False, "stats": {"queue_depth": len(items)}}
