"""
Social actions preview and approval-gated submit API (Social Media Entity Tools).
POST /actions/preview, POST /actions/submit (403 if not approved), GET /actions/{id}.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from hg_core.security import KeystoreError, SocialAccountNotFoundError, SocialAccountStateError
from hg_core.social import RedditAdapter, XAdapter, FacebookAdapter
from hg_core.social.base import SocialDraft
from hg_gateway.approval_service import ApprovalService, STATUS_APPROVED

router = APIRouter(tags=["social-entity"])


def _tenant_id(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str:
    return (x_tenant_id or "").strip() or "default"


class PreviewBody(BaseModel):
    platform: str
    action_type: str
    content: str
    target_uri: Optional[str] = None
    entity_id: Optional[str] = None


class SubmitBody(BaseModel):
    approval_id: str
    platform: str
    action_type: str
    content: str
    target_uri: Optional[str] = None


class FacebookLoginBody(BaseModel):
    entity_id: str
    account_alias: Optional[str] = None
    social_account_id: Optional[str] = None
    session_id: Optional[str] = None


class FacebookNotificationsBody(BaseModel):
    entity_id: str
    account_alias: Optional[str] = None
    social_account_id: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = 20


def _adapter_for_platform(platform: str):
    p = (platform or "").lower()
    if p == "reddit":
        return RedditAdapter()
    if p in ("x", "twitter"):
        return XAdapter()
    if p == "facebook":
        return FacebookAdapter()
    raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


def _map_social_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SocialAccountNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, SocialAccountStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, KeystoreError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.post("/actions/preview")
def social_preview(
    body: PreviewBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Build preview; optionally create approval_request and return approval_required + preview."""
    adapter = _adapter_for_platform(body.platform)
    draft = SocialDraft(platform=body.platform, action_type=body.action_type, content=body.content, target_uri=body.target_uri)
    preview = adapter.preview(draft)
    approval_required = True
    approval_id = None
    if body.entity_id:
        try:
            svc = ApprovalService()
            row = svc.create_request(
                entity_id=body.entity_id,
                action_kind="social_post",
                preview_json=preview,
                tenant_id=_tenant_id(x_tenant_id),
                target_platform=body.platform,
            )
            approval_id = (row or {}).get("approval_id")
        except Exception:
            pass
    return {
        "preview": preview,
        "approval_required": approval_required,
        "approval_id": approval_id,
    }


@router.post("/actions/submit")
def social_submit(
    body: SubmitBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Submit only if approval_id is approved; else 403 blocked_until_approved."""
    tenant = _tenant_id(x_tenant_id)
    svc = ApprovalService()
    row = svc.get_request(body.approval_id, tenant_id=tenant)
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if row.get("status") != STATUS_APPROVED:
        raise HTTPException(
            status_code=403,
            detail="blocked_until_approved",
        )
    adapter = _adapter_for_platform(body.platform)
    draft = SocialDraft(platform=body.platform, action_type=body.action_type, content=body.content, target_uri=body.target_uri)
    result = adapter.submit(draft, approval_id=body.approval_id, approved=True)
    return result


@router.post("/facebook/login")
def facebook_login(
    body: FacebookLoginBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Run a supervised Facebook login flow using the assigned keystore account."""
    tenant = _tenant_id(x_tenant_id)
    try:
        adapter = FacebookAdapter()
        return adapter.login(
            tenant_id=tenant,
            entity_id=body.entity_id,
            account_alias=body.account_alias,
            social_account_id=body.social_account_id,
            session_id=body.session_id,
        )
    except Exception as exc:
        raise _map_social_error(exc) from exc


@router.post("/facebook/read-notifications")
def facebook_read_notifications(
    body: FacebookNotificationsBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Read Facebook notifications for the assigned keystore account."""
    tenant = _tenant_id(x_tenant_id)
    try:
        adapter = FacebookAdapter()
        return adapter.read_notifications(
            tenant_id=tenant,
            entity_id=body.entity_id,
            account_alias=body.account_alias,
            social_account_id=body.social_account_id,
            session_id=body.session_id,
            limit=body.limit,
        )
    except Exception as exc:
        raise _map_social_error(exc) from exc


@router.get("/actions/{action_id}")
def get_social_action(
    action_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Return state, screenshots, trace, proof bundle refs (stub)."""
    return {
        "social_action_id": action_id,
        "state": "completed",
        "proof_refs": [],
    }
