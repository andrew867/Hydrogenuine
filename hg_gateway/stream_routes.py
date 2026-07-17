"""
SSE and WebSocket endpoints for /v1.

Event types: message.delta, message.final, tool.start, tool.result, agent.status,
approval.created, approval.resolved. Optional replay from events table when store supports it.
Pack3: tenant-scoped; cross-tenant chat access returns 403.
"""

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from hg_gateway import sse_hub
from hg_gateway.store import get_store
from hg_gateway.auth import verify_api_key, get_tenant_context
from hg_core.tenancy.context import TenantContext
from hg_gateway.routes import _build_swarm_workspace, _ensure_chat_accessible
from hg_gateway import swarm_bus
from hg_gateway.quotas_enforcement import check_stream_enter, consume_stream_enter, release_stream
from hg_core.security.redaction import redact_json

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _redact_sse_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields in SSE payloads (Pack3)."""
    return redact_json(payload) if isinstance(payload, dict) else payload


async def _sse_generator(tenant_id: str, chat_id: str, store: Any, replay: bool = True):
    try:
        if replay and hasattr(store, "event_list"):
            try:
                for ev in store.event_list(tenant_id, chat_id):
                    event_type = ev.get("event_type") or "event"
                    payload = _redact_sse_payload(ev.get("payload") or {})
                    data = json.dumps(payload)
                    yield f"event: {event_type}\ndata: {data}\n\n"
            except Exception:
                pass
        q = sse_hub.subscribe(chat_id)
        try:
            while True:
                try:
                    event_type, payload = await asyncio.wait_for(q.get(), timeout=30.0)
                    payload = _redact_sse_payload(payload) if isinstance(payload, dict) else payload
                    data = json.dumps(payload)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            sse_hub.unsubscribe(chat_id, q)
    finally:
        release_stream(store, tenant_id)


@router.get("/stream")
async def sse_stream_query(
    chat_id: Optional[str] = Query(None, alias="chat_id"),
    replay: bool = Query(True),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    """SSE endpoint: GET /v1/stream?chat_id=... Optional replay from persisted events. Tenant-scoped."""
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id required")
    store = get_store()
    _ensure_chat_accessible(store, tenant_context.tenant_id, chat_id)
    allowed, code = check_stream_enter(store, tenant_context.tenant_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"code": code, "message": "Tenant concurrent streams quota exceeded"},
            headers={"Retry-After": "60"},
        )
    consume_stream_enter(store, tenant_context.tenant_id)
    return StreamingResponse(
        _sse_generator(tenant_context.tenant_id, chat_id, store, replay=replay),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/chats/{chat_id}/stream")
async def sse_stream(
    chat_id: str,
    replay: bool = Query(True),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    """SSE endpoint: stream events for this chat. Tenant-scoped; 403 if chat belongs to another tenant."""
    store = get_store()
    _ensure_chat_accessible(store, tenant_context.tenant_id, chat_id)
    allowed, code = check_stream_enter(store, tenant_context.tenant_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"code": code, "message": "Tenant concurrent streams quota exceeded"},
            headers={"Retry-After": "60"},
        )
    consume_stream_enter(store, tenant_context.tenant_id)
    return StreamingResponse(
        _sse_generator(tenant_context.tenant_id, chat_id, store, replay=replay),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


async def _swarm_sse_generator(tenant_id: str, swarm_run_id: str, store: Any, replay: bool = True):
    seq = 0
    if replay:
        try:
            workspace = _build_swarm_workspace(store, tenant_id, swarm_run_id)
            data = json.dumps({"workspace": workspace})
            yield f"id: swarm-{swarm_run_id}-{seq}\nevent: swarm.workspace\ndata: {data}\n\n"
            seq += 1
        except HTTPException:
            pass
    q = swarm_bus.subscribe(tenant_id, swarm_run_id)
    try:
        while True:
            try:
                event_type, payload = await asyncio.wait_for(q.get(), timeout=30.0)
                data = json.dumps(payload)
                yield f"id: swarm-{swarm_run_id}-{seq}\nevent: {event_type}\ndata: {data}\n\n"
                seq += 1
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"
    finally:
        swarm_bus.unsubscribe(tenant_id, swarm_run_id, q)
        release_stream(store, tenant_id)


@router.get("/swarms/{swarm_run_id}/stream")
async def sse_swarm_stream(
    swarm_run_id: str,
    replay: bool = Query(True),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    """SSE endpoint: live swarm workspace updates for agent cards."""
    store = get_store()
    _build_swarm_workspace(store, tenant_context.tenant_id, swarm_run_id)
    allowed, code = check_stream_enter(store, tenant_context.tenant_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"code": code, "message": "Tenant concurrent streams quota exceeded"},
            headers={"Retry-After": "60"},
        )
    consume_stream_enter(store, tenant_context.tenant_id)
    return StreamingResponse(
        _swarm_sse_generator(tenant_context.tenant_id, swarm_run_id, store, replay=replay),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket: client sends { chat_id, action, ... }; server sends event stream for that chat."""
    await websocket.accept()
    chat_id: str | None = None
    q: asyncio.Queue | None = None
    recv_task: asyncio.Task | None = None

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "ping", "data": {}})
                continue
            action = msg.get("action")
            if action == "subscribe" and msg.get("chat_id"):
                if q:
                    if chat_id:
                        sse_hub.unsubscribe(chat_id, q)
                    recv_task and recv_task.cancel()
                chat_id = msg["chat_id"]
                q = sse_hub.subscribe(chat_id)
                async def forward():
                    try:
                        while True:
                            event_type, payload = await q.get()
                            await websocket.send_json({"event": event_type, "data": payload})
                    except asyncio.CancelledError:
                        pass
                recv_task = asyncio.create_task(forward())
                await websocket.send_json({"event": "subscribed", "data": {"chat_id": chat_id}})
            elif action == "ping":
                await websocket.send_json({"event": "pong", "data": {}})
    except WebSocketDisconnect:
        pass
    finally:
        if chat_id and q:
            sse_hub.unsubscribe(chat_id, q)
        if recv_task:
            recv_task.cancel()
