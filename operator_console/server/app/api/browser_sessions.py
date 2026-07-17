"""
Browser session API routes (Social Media Entity Tools).
Create/get browser sessions and drive supervised runtime actions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from hg_core.browser import BrowserRuntime
from hg_core.browser.playwright_runtime import get_playwright_runtime

router = APIRouter(tags=["browser-sessions"])


def _tenant_id(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str:
    return (x_tenant_id or "").strip() or "default"


class CreateSessionBody(BaseModel):
    entity_id: str
    platform: str


class NavigateBody(BaseModel):
    url: str


class CaptureBody(BaseModel):
    label: str


class PauseBody(BaseModel):
    reason: str


def _runtime() -> BrowserRuntime:
    return get_playwright_runtime()


@router.post("")
def create_session(
    body: CreateSessionBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Create a browser session; returns session_id."""
    tenant = _tenant_id(x_tenant_id)
    session_id = _runtime().start_session(body.entity_id, body.platform, tenant_id=tenant)
    return {"browser_session_id": session_id, "entity_id": body.entity_id, "platform": body.platform}


@router.get("/{session_id}")
def get_session_state(
    session_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Get browser session state from gateway DB."""
    tenant = _tenant_id(x_tenant_id)
    state = _runtime().get_session_state(session_id, tenant_id=tenant)
    if not state:
        raise HTTPException(status_code=404, detail="Browser session not found")
    return state


@router.post("/{session_id}/navigate")
def navigate_session(
    session_id: str,
    body: NavigateBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Navigate a session to a URL."""
    tenant = _tenant_id(x_tenant_id)
    try:
        result = _runtime().navigate(session_id, body.url, tenant_id=tenant)
        state = _runtime().get_session_state(session_id, tenant_id=tenant)
        return {"ok": result.ok, "result": result.data or {}, "session": state}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/capture")
def capture_session(
    session_id: str,
    body: CaptureBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Capture screenshot and snapshot artifacts for a session."""
    tenant = _tenant_id(x_tenant_id)
    try:
        result = _runtime().capture(session_id, body.label, tenant_id=tenant)
        return {
            "ok": result.ok,
            "screenshot_path": result.screenshot_path,
            "snapshot_path": result.snapshot_path,
            "result": result.data or {},
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/pause")
def pause_session(
    session_id: str,
    body: PauseBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Pause a browser session and mark it as awaiting human input."""
    tenant = _tenant_id(x_tenant_id)
    try:
        _runtime().pause_for_human_gate(session_id, body.reason, tenant_id=tenant)
        return {"browser_session_id": session_id, "paused": True, "reason": body.reason}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/artifacts")
def list_session_artifacts(
    session_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """List proof artifacts associated with a browser session."""
    tenant = _tenant_id(x_tenant_id)
    state = _runtime().get_session_state(session_id, tenant_id=tenant)
    if not state:
        raise HTTPException(status_code=404, detail="Browser session not found")
    return {"items": _runtime().list_artifacts(session_id, tenant_id=tenant)}


@router.post("/{session_id}/resume")
def resume_session(
    session_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Resume after human gate."""
    tenant = _tenant_id(x_tenant_id)
    try:
        _runtime().resume_session(session_id, tenant_id=tenant)
        return {"browser_session_id": session_id, "resumed": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
