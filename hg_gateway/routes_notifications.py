"""
GET /v1/stream/notifications — tenant-scoped SSE for approvals, exports, step-up, session hints.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from hg_core.tenancy.context import TenantContext
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway import notification_bus
from hg_gateway.store import get_store

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _pending_approval_notifications(store: Any, tenant_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    if not hasattr(store, "approval_list"):
        return []
    try:
        result = store.approval_list(tenant_id, status_filter="pending", limit=limit)
        rows = result.get("approvals", []) if isinstance(result, dict) else (result or [])
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        approval_id = row.get("id") or row.get("approval_id")
        if not approval_id:
            continue
        out.append({
            "id": f"approval-{approval_id}",
            "type": "approval.created",
            "title": row.get("title") or f"Approval pending ({row.get('kind') or 'review'})",
            "href": f"/approvals",
            "approval_id": approval_id,
            "kind": row.get("kind"),
            "created_at": row.get("created_at") or row.get("createdAt"),
        })
    return out


async def _notification_sse_generator(tenant_id: str, store: Any, replay: bool = True):
    if replay:
        for item in _pending_approval_notifications(store, tenant_id):
            data = json.dumps(item)
            yield f"event: notification\ndata: {data}\n\n"
    q = notification_bus.subscribe(tenant_id)
    try:
        while True:
            try:
                event_type, payload = await asyncio.wait_for(q.get(), timeout=30.0)
                data = json.dumps({"type": event_type, **(payload or {})})
                yield f"event: notification\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"
    finally:
        notification_bus.unsubscribe(tenant_id, q)


@router.get("/stream/notifications")
async def sse_notifications(
    replay: bool = Query(True),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    """SSE endpoint: live tenant notifications (approvals, exports, step-up)."""
    store = get_store()
    return StreamingResponse(
        _notification_sse_generator(tenant_context.tenant_id, store, replay=replay),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def emit_tenant_notification(tenant_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """Emit a notification to all SSE subscribers for this tenant."""
    if not tenant_id:
        return
    notification_bus.emit(tenant_id, event_type, payload)
