"""L10 Events API: POST /events, GET /events, GET /events/stream. Phase 8."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ..core.auth import require_api_key, require_api_key_or_query
from ..services.event_store import append_event, list_events, stream_events_sse

router = APIRouter()


@router.post("")
def post_event(
    body: dict,
    _=Depends(require_api_key),
):
    """Accept an event; validate and persist. Returns { accepted, event_id }."""
    tenant_id = (body.get("tenant_id") or "").strip() or "default"
    actor_id = (body.get("actor_id") or "").strip() or "api"
    correlation_id = (body.get("correlation_id") or "").strip()
    run_id = (body.get("run_id") or "").strip() or None
    payload = body.get("payload")
    if payload is None:
        payload = dict(body)
        for k in ("tenant_id", "actor_id", "correlation_id", "run_id", "event_id"):
            payload.pop(k, None)
    if not isinstance(payload, dict):
        payload = {}
    event_type = (body.get("event_type") or "internal").strip() or "internal"
    event_id = (body.get("event_id") or "").strip() or None
    try:
        eid = append_event(
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            run_id=run_id,
            payload=payload,
            event_type=event_type,
            event_id=event_id,
        )
    except Exception as e:
        return {"accepted": False, "error": str(e)}
    return {"accepted": True, "event_id": eid}


@router.get("")
def get_events(
    correlation_id: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    _=Depends(require_api_key),
):
    """List events by correlation_id and/or run_id."""
    events = list_events(correlation_id=correlation_id, run_id=run_id, limit=limit)
    return {"ok": True, "events": events}


@router.get("/stream")
def get_events_stream(
    _=Depends(require_api_key_or_query),
):
    """SSE stream of new events (global tail)."""
    return StreamingResponse(
        stream_events_sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
