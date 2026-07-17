"""
Steering API: events, authority config, profiles. L10: POST /steering (Phase 8).
See docs/specs/operator_console_steering_api_spec.md.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from ..core.auth import require_api_key
from ..services.steering_service import (
    get_steering_events,
    get_authority_config,
    list_steering_profiles,
    get_steering_profile,
    get_default_steering_profile,
    put_steering_profile,
    get_constitution,
    put_constitution,
    get_origin_myths,
    put_origin_myths,
    submit_steering_event,
)

router = APIRouter()


@router.post("")
def post_steering(body: dict, _=Depends(require_api_key)):
    """Submit a steering event (cancel/pause/resume/inject) for a run. Returns { ok, steering_id }."""
    run_id = (body.get("run_id") or "").strip()
    if not run_id:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "run_id is required"})
    kind = (body.get("kind") or "inject").strip().lower()
    payload = body.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    result = submit_steering_event(
        run_id=run_id,
        kind=kind,
        payload=payload,
        tenant_id=(body.get("tenant_id") or "default").strip(),
        actor_id=(body.get("actor_id") or "api").strip(),
        correlation_id=(body.get("correlation_id") or "").strip(),
        node_id=(body.get("node_id") or "").strip() or None,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"code": "STEERING_FAILED", "message": result.get("error", "submit failed")})
    return result


@router.get("/events")
def steering_events(
    limit: int = Query(100, ge=1, le=500),
    _=Depends(require_api_key),
):
    """Recent steering telemetry events (steering_events.jsonl). Newest first."""
    events = get_steering_events(limit=limit)
    return {"ok": True, "events": events}


@router.get("/authority-config")
def authority_config(_=Depends(require_api_key)):
    """Current authority configuration (read-only)."""
    config = get_authority_config()
    return {"ok": True, "config": config}


@router.get("/profiles")
def steering_profiles_list(_=Depends(require_api_key)):
    """List steering profile IDs (agents with a profile file)."""
    profiles = list_steering_profiles()
    return {"ok": True, "profiles": profiles}


@router.get("/profiles/{agent_id}")
def steering_profile_detail(agent_id: str, _=Depends(require_api_key)):
    """Steering profile for the given agent (read-only)."""
    profile = get_steering_profile(agent_id)
    if profile is None:
        profile = get_default_steering_profile(agent_id)
    return {"ok": True, "agent_id": agent_id, "profile": profile}


@router.put("/profiles/{agent_id}")
def steering_profile_update(agent_id: str, body: dict, _=Depends(require_api_key)):
    """Update steering profile. Body: { profile: SteeringProfile }, optional updated_by."""
    profile = body.get("profile")
    if not isinstance(profile, dict):
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "profile object required"})
    updated_by = (body.get("updated_by") or "api").strip()
    if not put_steering_profile(agent_id, profile, updated_by=updated_by):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "agent_id invalid or write failed"})
    return {"ok": True, "agent_id": agent_id}


@router.get("/profiles/{agent_id}/constitution")
def constitution_get(agent_id: str, _=Depends(require_api_key)):
    """Style Constitution (plain text) for the agent."""
    content = get_constitution(agent_id)
    if content is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "agent_id invalid"})
    return {"ok": True, "agent_id": agent_id, "content": content or ""}


@router.put("/profiles/{agent_id}/constitution")
def constitution_put(agent_id: str, body: dict, _=Depends(require_api_key)):
    """Update Style Constitution. Body: { content: string }."""
    content = body.get("content", "")
    if not put_constitution(agent_id, str(content)):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "agent_id invalid or write failed"})
    return {"ok": True, "agent_id": agent_id}


@router.get("/profiles/{agent_id}/origin-myths")
def origin_myths_get(agent_id: str, _=Depends(require_api_key)):
    """Origin myths (JSON array of strings) for the agent."""
    myths = get_origin_myths(agent_id)
    if myths is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "agent_id invalid"})
    return {"ok": True, "agent_id": agent_id, "myths": myths}


@router.put("/profiles/{agent_id}/origin-myths")
def origin_myths_put(agent_id: str, body: dict, _=Depends(require_api_key)):
    """Update Origin myths. Body: { myths: string[] }."""
    myths = body.get("myths")
    if not isinstance(myths, list):
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "myths array required"})
    if not put_origin_myths(agent_id, [str(m) for m in myths]):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "agent_id invalid or write failed"})
    return {"ok": True, "agent_id": agent_id}
