from __future__ import annotations

import uuid
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.orchestration import run_turn
from hg_gateway.store import get_store
from hg_core.tenancy.context import TenantContext
from hg_gateway.community import router as community_router

router = APIRouter(dependencies=[Depends(verify_api_key)])
router.include_router(community_router)


def _message_dict(row: Any) -> Dict[str, Any]:
    if isinstance(row, dict):
        return row
    return {
        "message_id": getattr(row, "message_id", None),
        "chat_id": getattr(row, "chat_id", None),
        "role": getattr(row, "role", None),
        "created_at": getattr(row, "created_at", None),
        "content": getattr(row, "content", None),
        "agent_id": getattr(row, "agent_id", None),
        "tool_name": getattr(row, "tool_name", None),
        "tool_payload": getattr(row, "tool_payload", None),
        "tool_result": getattr(row, "tool_result", None),
        "approvals_required": getattr(row, "approvals_required", None),
    }


def _build_messages(store: Any, tenant_id: str, chat_id: str, user_content: str) -> List[Dict[str, str]]:
    messages = [{"role": m.get("role", "user"), "content": str(m.get("content") or "")} for m in store.message_list(tenant_id, chat_id)]
    messages.append({"role": "user", "content": user_content})
    return messages


def _require_chat(store: Any, tenant_id: str, chat_id: str) -> Dict[str, Any]:
    chat = store.chat_get(tenant_id, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


def _ensure_chat_accessible(store: Any, tenant_id: str, chat_id: str) -> None:
    _require_chat(store, tenant_id, chat_id)


def _build_swarm_workspace(store: Any, tenant_id: str, swarm_run_id: str) -> Dict[str, Any]:
    chats = [chat for chat in store.chat_list(tenant_id) if chat.get("swarm_run_id") == swarm_run_id]
    return {"swarm_run_id": swarm_run_id, "chats": chats, "messages": {}}


def _attach_assistant_research_sources(*args: Any, **kwargs: Any) -> None:
    return None


def _plan_research_request(request: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"kind": "research", "request": request, "steps": [{"title": "Review request", "status": "planned"}]}


def _build_research_execution_plan(request: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"kind": "research_execution", "request": request, "steps": [{"title": "Draft answer", "status": "planned"}]}


def _build_document_decomposition_plan(request: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"kind": "document_decomposition", "request": request, "steps": [{"title": "Extract document tasks", "status": "planned"}]}


@router.get("/chats")
def list_chats(tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    return {"chats": store.chat_list(tenant_context.tenant_id)}


@router.post("/chats")
def create_chat(
    body: Dict[str, Any] = Body(default_factory=dict),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    title = str(body.get("title") or "New chat").strip() or "New chat"
    store = get_store()
    chat_id = store.chat_create(tenant_context.tenant_id, title=title)
    return {"chat_id": chat_id, "chat": store.chat_get(tenant_context.tenant_id, chat_id)}


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    return {"chat": _require_chat(store, tenant_context.tenant_id, chat_id)}


@router.patch("/chats/{chat_id}")
def update_chat(
    chat_id: str,
    body: Dict[str, Any] = Body(default_factory=dict),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    title = body.get("title")
    if title is not None:
        store.chat_update(tenant_context.tenant_id, chat_id, str(title))
    return {"chat": store.chat_get(tenant_context.tenant_id, chat_id)}


@router.post("/chats/{chat_id}/archive")
def archive_chat(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    if hasattr(store, "chat_patch"):
        store.chat_patch(tenant_context.tenant_id, chat_id, archived=True)
    return {"chat_id": chat_id, "status": "archived"}


@router.post("/chats/{chat_id}/retry")
async def retry_chat(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    messages = store.message_list(tenant_context.tenant_id, chat_id)
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    if not last_user:
        raise HTTPException(status_code=400, detail="no user message to retry")
    row = await run_turn(
        tenant_context.tenant_id,
        chat_id,
        "primary",
        "Assistant",
        [{"role": m.get("role", "user"), "content": str(m.get("content") or "")} for m in messages],
        provider="stub",
    )
    return {"assistant_message": _message_dict(row)}


@router.post("/chats/{chat_id}/branch")
def branch_chat(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    chat = _require_chat(store, tenant_context.tenant_id, chat_id)
    branch_id = store.chat_create(tenant_context.tenant_id, title=f"{chat.get('title', 'Chat')} branch")
    for message in store.message_list(tenant_context.tenant_id, chat_id):
        store.message_add(tenant_context.tenant_id, branch_id, message.get("role", "user"), str(message.get("content") or ""), agent_id=message.get("agent_id"))
    return {"chat_id": branch_id, "source_chat_id": chat_id}


@router.post("/chats/{chat_id}/attachments")
def add_attachment(
    chat_id: str,
    body: Dict[str, Any] = Body(default_factory=dict),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    attachment_id = f"att_{uuid.uuid4().hex[:12]}"
    store.message_add(tenant_context.tenant_id, chat_id, "tool", f"Attachment registered: {body.get('name') or attachment_id}", tool_name="attachment", tool_payload={"attachment_id": attachment_id, **body})
    return {"attachment": {"attachment_id": attachment_id, "name": body.get("name"), "status": "registered"}}


@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    if not store.chat_delete(tenant_context.tenant_id, chat_id):
        raise HTTPException(status_code=404, detail="chat not found")
    return None


@router.get("/chats/{chat_id}/messages")
def list_messages(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    return {"messages": store.message_list(tenant_context.tenant_id, chat_id)}


@router.post("/chats/{chat_id}/messages")
async def post_message(
    chat_id: str,
    request: Request,
    body: Dict[str, Any] = Body(default_factory=dict),
    x_hg_model_provider: Optional[str] = Header(default=None),
    x_hg_model: Optional[str] = Header(default=None),
    x_hg_base_url: Optional[str] = Header(default=None),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    content = str(body.get("content") or body.get("message") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    user_row = store.message_add(tenant_context.tenant_id, chat_id, "user", content)
    emitted: List[Dict[str, Any]] = []

    def emit(event_type: str, payload: Dict[str, Any]) -> None:
        emitted.append({"type": event_type, "payload": payload})

    assistant_row = await run_turn(
        tenant_context.tenant_id,
        chat_id,
        "primary",
        "Assistant",
        _build_messages(store, tenant_context.tenant_id, chat_id, content),
        provider=body.get("provider") or x_hg_model_provider,
        model=body.get("model") or x_hg_model,
        base_url=body.get("base_url") or x_hg_base_url,
        emit=emit,
        max_tokens=int(body.get("max_tokens") or 1024),
        temperature=float(body.get("temperature") or 0.7),
    )
    return {
        "chat_id": chat_id,
        "message": _message_dict(user_row),
        "assistant_message": _message_dict(assistant_row),
        "events": emitted,
        "request_id": getattr(request.state, "request_id", None),
    }


@router.post("/chats/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    body: Dict[str, Any] = Body(default_factory=dict),
    x_hg_model_provider: Optional[str] = Header(default=None),
    x_hg_model: Optional[str] = Header(default=None),
    x_hg_base_url: Optional[str] = Header(default=None),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    content = str(body.get("content") or body.get("message") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    user_row = store.message_add(tenant_context.tenant_id, chat_id, "user", content)

    async def events():
        queue: List[Dict[str, Any]] = []

        def emit(event_type: str, payload: Dict[str, Any]) -> None:
            queue.append({"type": event_type, "payload": payload})

        yield f"event: message.created\ndata: {json.dumps({'message': _message_dict(user_row)})}\n\n"
        assistant_row = await run_turn(
            tenant_context.tenant_id,
            chat_id,
            "primary",
            "Assistant",
            _build_messages(store, tenant_context.tenant_id, chat_id, content),
            provider=body.get("provider") or x_hg_model_provider,
            model=body.get("model") or x_hg_model,
            base_url=body.get("base_url") or x_hg_base_url,
            emit=emit,
            max_tokens=int(body.get("max_tokens") or 1024),
            temperature=float(body.get("temperature") or 0.7),
        )
        for item in queue:
            yield f"event: {item['type']}\ndata: {json.dumps(item['payload'])}\n\n"
        yield f"event: done\ndata: {json.dumps({'assistant_message': _message_dict(assistant_row)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/chats/{chat_id}/stop")
def stop_chat(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    row = store.message_add(tenant_context.tenant_id, chat_id, "tool", "Generation stopped by operator.", tool_name="generation.stop")
    return {"chat_id": chat_id, "status": "stopped", "message": _message_dict(row)}


@router.get("/chats/{chat_id}/agents")
def list_agents(chat_id: str, tenant_context: TenantContext = Depends(get_tenant_context)):
    store = get_store()
    _require_chat(store, tenant_context.tenant_id, chat_id)
    return {"agents": store.agent_list(tenant_context.tenant_id, chat_id)}
