"""
Control Surface Pack 1: Ops Console API service — list entities/groups/threads/work items, control and steering.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.work_items.work_items import create_work_item

from .data_model import EntityState, GroupState, ThreadState


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def get_entities(
    workspace_root: Path,
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Any:
    """List entity states with optional filters and pagination.
    When cursor is None and limit is 50: returns list (backward compat).
    When cursor is set or limit != 50: returns { items, next_cursor }.
    """
    root = _materialized_root(workspace_root)
    work_items = _load_jsonl(root / "work_items.jsonl")
    entities_by_agent: Dict[str, EntityState] = {}
    for wi in work_items:
        owner = wi.get("owner_agent_id") or wi.get("scope_id") or "default"
        if owner not in entities_by_agent:
            entities_by_agent[owner] = {
                "id": owner,
                "role": "agent",
                "group_id": wi.get("scope_id") or "default",
                "status": "active",
                "autonomy_level": "normal",
                "current_work_item_id": None,
                "last_event_ts": wi.get("updated_ts", ""),
            }
        if wi.get("status") in ("active", "blocked"):
            entities_by_agent[owner]["current_work_item_id"] = wi.get("work_item_id")
            entities_by_agent[owner]["last_event_ts"] = wi.get("updated_ts", "")
    entity_registry = workspace_root / "memory" / "overseer" / "entity_registry.json"
    if entity_registry.exists():
        try:
            reg = json.loads(entity_registry.read_text(encoding="utf-8"))
            for e in reg.get("entities", []):
                eid = e.get("id", "")
                if eid and eid not in entities_by_agent:
                    entities_by_agent[eid] = {
                        "id": eid,
                        "role": e.get("role", "agent"),
                        "group_id": e.get("group_id", "default"),
                        "status": e.get("status", "active"),
                        "autonomy_level": e.get("autonomy_level", "normal"),
                        "current_work_item_id": None,
                        "last_event_ts": e.get("last_event_ts", ""),
                    }
        except Exception:
            pass
    out = list(entities_by_agent.values())
    if group_id:
        out = [e for e in out if e.get("group_id") == group_id]
    if status:
        out = [e for e in out if (e.get("status") or "active") == status]
    out.sort(key=lambda e: (e.get("group_id", ""), e.get("id", "")))
    start = 0
    if cursor:
        for i, e in enumerate(out):
            if e.get("id") == cursor:
                start = i + 1
                break
    page = out[start : start + limit + 1]
    next_cursor = page[limit].get("id") if len(page) > limit else None
    items = page[:limit]
    # Backward compat: no pagination requested -> return list
    if cursor is None and limit == 50 and status is None:
        return out[:50]
    return {"items": items, "next_cursor": next_cursor}


def get_groups(
    workspace_root: Path,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Any:
    """List group states. With cursor/limit returns { items, next_cursor }; else list (backward compat)."""
    root = _materialized_root(workspace_root)
    groups: Dict[str, GroupState] = {}
    work_items = _load_jsonl(root / "work_items.jsonl")
    for wi in work_items:
        sid = wi.get("scope_id") or "default"
        if sid not in groups:
            groups[sid] = {"id": sid, "members": [], "incidents_open": 0, "safeguards_active": 0, "budget_status": "ok"}
        owner = wi.get("owner_agent_id")
        if owner and owner not in groups[sid].get("members", []):
            groups[sid].setdefault("members", []).append(owner)
    incidents = _load_jsonl(root / "incidents.jsonl")
    for inc in incidents:
        if inc.get("status") not in ("resolved", "closed"):
            sid = inc.get("scope_id") or inc.get("scope_type") or "default"
            if sid in groups:
                groups[sid]["incidents_open"] = groups[sid].get("incidents_open", 0) + 1
    out = list(groups.values())
    out.sort(key=lambda g: g.get("id", ""))
    start = 0
    if cursor:
        for i, g in enumerate(out):
            if g.get("id") == cursor:
                start = i + 1
                break
    page = out[start : start + limit + 1]
    next_cursor = page[limit].get("id") if len(page) > limit else None
    items = page[:limit]
    if cursor is None and limit == 50:
        return out[:50]
    return {"items": items, "next_cursor": next_cursor}


def get_thread(workspace_root: Path, thread_id: str) -> Optional[ThreadState]:
    """Thread detail for operator view (redacted as needed)."""
    root = workspace_root / "memory" / "materialized" / "threads"
    path = root / f"{thread_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "thread_id": data.get("thread_id", thread_id),
            "participants": data.get("participants", []),
            "last_messages": data.get("last_messages", [])[-50:],
            "attachments_refs": data.get("attachments_refs", []),
        }
    except Exception:
        return None


def get_work_items(
    workspace_root: Path,
    group_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> Any:
    """Work queue; filter by group, entity, status. With cursor returns { items, next_cursor }; else list."""
    root = _materialized_root(workspace_root)
    items = _load_jsonl(root / "work_items.jsonl")
    if group_id:
        items = [w for w in items if w.get("scope_id") == group_id]
    if entity_id:
        items = [w for w in items if w.get("owner_agent_id") == entity_id]
    if status:
        items = [w for w in items if w.get("status") == status]
    items.sort(key=lambda w: w.get("updated_ts", ""), reverse=True)
    start = 0
    if cursor:
        for i, w in enumerate(items):
            if w.get("work_item_id") == cursor:
                start = i + 1
                break
    page = items[start : start + limit + 1]
    next_cursor = page[limit].get("work_item_id") if len(page) > limit else None
    result_items = page[:limit]
    if cursor is None and limit == 100 and status is None:
        return items[:limit]
    return {"items": result_items, "next_cursor": next_cursor}


def get_activity_feed(
    workspace_root: Path,
    limit: int = 50,
    cursor: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Paginated activity feed from audit/ledger events. Returns { items, next_cursor }."""
    root = _materialized_root(workspace_root)
    events: List[Dict[str, Any]] = []
    audit_path = root / "audit_events.jsonl"
    if audit_path.exists():
        for line in _load_jsonl(audit_path):
            if scope_id and line.get("scope_id") != scope_id:
                continue
            events.append({
                "event_id": line.get("event_id"),
                "action": line.get("action"),
                "ts": line.get("ts", ""),
                "scope_id": line.get("scope_id", ""),
                "payload": line.get("resource"),
            })
    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    start = 0
    if cursor:
        for i, e in enumerate(events):
            if e.get("event_id") == cursor:
                start = i + 1
                break
    page = events[start : start + limit + 1]
    next_cursor = page[limit].get("event_id") if len(page) > limit else None
    return {"items": page[:limit], "next_cursor": next_cursor}


def explain_block(
    workspace_root: Path,
    work_item_id: Optional[str] = None,
    action_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Explain why a work item or action is blocked. Returns BlockExplanation or None if ref not given."""
    ref_id = work_item_id or action_id
    if not ref_id:
        return None
    ref_type = "action" if (action_id and not work_item_id) else "work_item"
    root = _materialized_root(workspace_root)
    items = _load_jsonl(root / "work_items.jsonl")
    wi = next((w for w in items if w.get("work_item_id") == ref_id), None)
    if not wi:
        return {
            "ref_type": ref_type,
            "ref_id": ref_id,
            "blocked": False,
            "gate": "",
            "missing_evidence": [],
            "expiry_or_revalidation": None,
            "recommended_next_step": None,
        }
    blocked = wi.get("status") == "blocked"
    return {
        "ref_type": "work_item",
        "ref_id": wi.get("work_item_id", ref_id),
        "blocked": blocked,
        "gate": "work_item_blocked" if blocked else "",
        "missing_evidence": ["insufficient_robustness"] if blocked else [],
        "expiry_or_revalidation": None,
        "recommended_next_step": "Review and add verifier or override with expiry." if blocked else None,
    }


def control_pause(
    *,
    target: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    reason_artifact_id: Optional[str] = None,
    expiry_ts: Optional[str] = None,
) -> str:
    """Pause entity or group. Emit ENTITY_PAUSED (audited). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    target_type = target.get("type", "entity")
    target_id = target.get("id", "")
    return emit(
        "ENTITY_PAUSED",
        "control",
        target_id or "unknown",
        {"target": target, "reason_artifact_id": reason_artifact_id or "", "expiry_ts": expiry_ts or "", "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def control_resume(
    *,
    target: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Resume entity or group. Emit ENTITY_RESUMED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    target_id = target.get("id", "")
    return emit(
        "ENTITY_RESUMED",
        "control",
        target_id or "unknown",
        {"target": target, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def control_override(
    *,
    target: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    expiry_hours: int = 24,
    reason_artifact_id: Optional[str] = None,
) -> str:
    """Apply temporary override (with expiry). Emit CONTROL_OVERRIDE_APPLIED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    expiry_ts = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat().replace("+00:00", "Z")
    target_id = target.get("id", "")
    return emit(
        "CONTROL_OVERRIDE_APPLIED",
        "control",
        target_id or "override_" + ts[:10],
        {"target": target, "expiry_ts": expiry_ts, "reason_artifact_id": reason_artifact_id or "", "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def control_handoff_to_human(
    *,
    entity_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Create human intervention work item and emit HANDOFF_TO_HUMAN_REQUESTED. Returns work_item_id."""
    workspace_root = Path(workspace_root or ".")
    work_item_id = create_work_item(
        wi_type="task",
        title="Human intervention: " + reason[:80],
        description=reason,
        scope=scope,
        actor=actor,
        priority="high",
        workspace_root=workspace_root,
    )
    ts = _iso_ts()
    emit(
        "HANDOFF_TO_HUMAN_REQUESTED",
        "control",
        work_item_id,
        {"work_item_id": work_item_id, "entity_id": entity_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return work_item_id


def steering_assign_goal(
    *,
    target: Dict[str, Any],
    goal: str,
    constraints: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    ttl_hours: Optional[int] = None,
) -> str:
    """Assign goal/constraints to group or entity. Emit GOAL_ASSIGNED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    target_id = target.get("id", "")
    payload = {"target": target, "goal": goal, "constraints": constraints, "ts": ts}
    if ttl_hours is not None:
        payload["expiry_ts"] = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat().replace("+00:00", "Z")
    return emit(
        "GOAL_ASSIGNED",
        "steering",
        target_id or "goal_" + ts[:10],
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def steering_set_autonomy(
    *,
    target: Dict[str, Any],
    autonomy_level: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Set autonomy preset for group or entity. Emit AUTONOMY_LEVEL_SET. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    target_id = target.get("id", "")
    return emit(
        "AUTONOMY_LEVEL_SET",
        "steering",
        target_id or "autonomy_" + ts[:10],
        {"target": target, "autonomy_level": autonomy_level, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
