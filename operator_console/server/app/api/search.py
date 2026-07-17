"""Unified operator search: control-surface materialized index + runs, entities, approvals."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from hg_core.control_surface.search import search as control_surface_search
from hg_gateway.approval_summary import normalize_runtime_approval

from ..core.auth import require_api_key
from ..services.entities_service import list_entities
from ..services.run_ops import list_runs

router = APIRouter()


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _runtime_tenant_id() -> str:
    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _href_for_item(item: dict) -> str:
    item_type = str(item.get("type") or "")
    item_id = str(item.get("id") or "")
    if not item_id:
        return "/"
    routes = {
        "run": f"/runs/{item_id}",
        "entity": f"/entities/{item_id}",
        "incident": f"/incident-queue",
        "work_item": f"/ops-live?work_item={item_id}",
        "approval": f"/approvals",
        "workflow": f"/workflows",
    }
    return routes.get(item_type, "/")


@router.get("")
def unified_search(
    q: str = Query("", max_length=200),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = None,
    _=Depends(require_api_key),
):
    """Search entities, runs, incidents, work items, and runtime approvals."""
    root = _workspace_root()
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    q_lower = (q or "").strip().lower()

    if root is not None:
        try:
            cs = control_surface_search(root, q=q, limit=limit, cursor=cursor)
            for row in cs.get("items") or []:
                if not isinstance(row, dict):
                    continue
                key = (str(row.get("type") or ""), str(row.get("id") or ""))
                if key in seen or not key[1]:
                    continue
                seen.add(key)
                items.append({**row, "href": _href_for_item(row)})
        except Exception:
            pass

    try:
        for run in (list_runs(limit=500).get("runs") or [])[:200]:
            run_id = str(run.get("run_id") or "")
            graph_id = str(run.get("graph_id") or "")
            if not run_id:
                continue
            if q_lower and q_lower not in run_id.lower() and q_lower not in graph_id.lower():
                continue
            key = ("run", run_id)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "type": "run",
                    "id": run_id,
                    "title": graph_id or run_id,
                    "ts": run.get("started_at") or "",
                    "status": run.get("status"),
                    "href": f"/runs/{run_id}",
                }
            )
    except Exception:
        pass

    try:
        for entity in list_entities()[:200]:
            entity_id = str(entity.get("entity_id") or entity.get("id") or "")
            if not entity_id:
                continue
            if q_lower and q_lower not in entity_id.lower():
                continue
            key = ("entity", entity_id)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "type": "entity",
                    "id": entity_id,
                    "title": entity.get("name") or entity_id,
                    "ts": entity.get("last_activity") or "",
                    "status": entity.get("status"),
                    "href": f"/entities/{entity_id}",
                }
            )
    except Exception:
        pass

    try:
        from hg_gateway.store import get_store

        for approval in get_store().approval_list(_runtime_tenant_id(), status_filter="all")[:100]:
            row = normalize_runtime_approval(approval)
            aid = str(row.get("id") or row.get("approval_id") or "")
            summary = str(row.get("summary") or row.get("title") or row.get("kind") or "")
            workflow = str(row.get("workflow_id") or row.get("workflow") or "")
            if not aid:
                continue
            haystack = f"{aid} {summary} {workflow}".lower()
            if q_lower and q_lower not in haystack:
                continue
            key = ("approval", aid)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "type": "approval",
                    "id": aid,
                    "title": summary or aid,
                    "ts": row.get("createdAt") or row.get("timestamp") or "",
                    "status": row.get("status") or row.get("decision"),
                    "href": "/approvals",
                }
            )
    except Exception:
        pass

    items.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)
    page = items[:limit]
    next_cursor = items[limit].get("id") if len(items) > limit else None
    return {"ok": True, "items": page, "next_cursor": next_cursor, "q": q}
