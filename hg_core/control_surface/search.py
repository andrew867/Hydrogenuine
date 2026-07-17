"""
Control Surface Pack 12: Unified search over entities, groups, swarms, work items, actions, incidents.
Filtered by scope/tenant; query budget enforced; paginated.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .query_budget import consume_budget, get_request_budget

COST_PER_ROW = 1
DEFAULT_SEARCH_LIMIT = 50


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def search(
    workspace_root: Path,
    q: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    scope_id: Optional[str] = None,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified search over materialized entities, work items, incidents.
    q: optional text filter (substring match on id, title, summary); empty = all.
    scope_id: filter by scope (e.g. run id); RBAC-aware.
    Returns { items: [...], next_cursor }, each item has type, id, title/summary, ts.
    """
    root = Path(workspace_root) / "memory" / "materialized"
    q_lower = (q or "").strip().lower()
    items: List[Dict[str, Any]] = []
    seen: set = set()

    def matches(rec: Dict[str, Any], *fields: str) -> bool:
        if not q_lower:
            return True
        for f in fields:
            val = rec.get(f) or ""
            if isinstance(val, str) and q_lower in val.lower():
                return True
        return False

    # Work items
    wi_path = root / "work_items.jsonl"
    if wi_path.exists() and consume_budget(500):
        for r in _load_jsonl(wi_path):
            if scope_id and r.get("scope_id") != scope_id:
                continue
            if not matches(r, "work_item_id", "title"):
                continue
            key = ("wi", r.get("work_item_id", ""))
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "type": "work_item",
                "id": r.get("work_item_id"),
                "title": r.get("title", ""),
                "ts": r.get("updated_ts", ""),
                "status": r.get("status"),
            })
            if not consume_budget(COST_PER_ROW):
                break

    # Entities (from work_items owner/scope)
    entities_path = root / "work_items.jsonl"
    if entities_path.exists() and consume_budget(300):
        for r in _load_jsonl(entities_path):
            eid = r.get("owner_agent_id") or r.get("scope_id") or "default"
            if scope_id and r.get("scope_id") != scope_id:
                continue
            if not matches(r, "owner_agent_id", "scope_id"):
                continue
            key = ("entity", eid)
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "type": "entity",
                "id": eid,
                "title": eid,
                "ts": r.get("updated_ts", ""),
            })
            if not consume_budget(COST_PER_ROW):
                break

    # Incidents
    inc_path = root / "incidents.jsonl"
    if inc_path.exists() and consume_budget(200):
        for r in _load_jsonl(inc_path):
            if scope_id and r.get("scope_id") != scope_id:
                continue
            if not matches(r, "incident_id", "title"):
                continue
            key = ("incident", r.get("incident_id", ""))
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "type": "incident",
                "id": r.get("incident_id"),
                "title": r.get("title", ""),
                "ts": r.get("ts", r.get("updated_ts", "")),
                "status": r.get("status"),
            })
            if not consume_budget(COST_PER_ROW):
                break

    items.sort(key=lambda x: x.get("ts", ""), reverse=True)
    start = 0
    if cursor:
        for i, it in enumerate(items):
            if it.get("id") == cursor:
                start = i + 1
                break
    page = items[start : start + limit + 1]
    next_cursor = page[limit].get("id") if len(page) > limit else None
    return {"items": page[:limit], "next_cursor": next_cursor}
