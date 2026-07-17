"""
Pack 15.3: Steering profiles API — CRUD, tenant defaults, per-chat override.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from hg_core.tenancy.context import TenantContext
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.steering_store import (
    STEERING_TYPES,
    get_chat_steering_profile_ids,
    get_tenant_default_profile_ids,
    resolve_steering_profiles,
    set_chat_steering_profile_ids,
    set_tenant_default_profile_ids,
    steering_profile_create,
    steering_profile_delete,
    steering_profile_get,
    steering_profile_list,
    steering_profile_update,
)

router = APIRouter(prefix="/steering", tags=["steering"], dependencies=[Depends(verify_api_key)])


@router.get("/profiles")
def list_profiles(
    tenant_context: TenantContext = Depends(get_tenant_context),
    include_global: bool = True,
) -> Dict[str, Any]:
    """List steering profiles for the tenant (and global defaults if include_global)."""
    profiles = steering_profile_list(tenant_id=tenant_context.tenant_id, include_global=include_global)
    return {"profiles": profiles}


@router.post("/profiles")
def create_profile(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Create a steering profile. Use tenant_id in body = null for global (optional)."""
    profile_id = (body.get("profile_id") or "").strip()
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id is required")
    if "tenant_id" in body and body["tenant_id"] is None:
        tenant_id = None  # global default
    elif "tenant_id" in body and body["tenant_id"] != tenant_context.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create profile for another tenant")
    else:
        tenant_id = tenant_context.tenant_id
    type_ = (body.get("type") or "custom").strip().lower()
    if type_ not in STEERING_TYPES:
        type_ = "custom"
    strength = float(body.get("strength", 0.5))
    target = body.get("target") if isinstance(body.get("target"), dict) else None
    prompt_fragments = body.get("prompt_fragments")
    if prompt_fragments is not None and not isinstance(prompt_fragments, list):
        prompt_fragments = None
    classifier_thresholds = body.get("classifier_thresholds") if isinstance(body.get("classifier_thresholds"), dict) else None
    try:
        profile = steering_profile_create(
            profile_id=profile_id,
            tenant_id=tenant_id,
            type=type_,
            strength=strength,
            target=target,
            prompt_fragments=prompt_fragments,
            classifier_thresholds=classifier_thresholds,
        )
    except Exception as e:
        if "UNIQUE" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Profile {profile_id} already exists")
        raise
    return profile


@router.get("/profiles/{profile_id}")
def get_profile(
    profile_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get a steering profile by id. Must belong to tenant or be global."""
    profile = steering_profile_get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if profile.get("tenant_id") is not None and profile["tenant_id"] != tenant_context.tenant_id:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


@router.patch("/profiles/{profile_id}")
def update_profile(
    profile_id: str,
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Update a steering profile. Must belong to tenant or be global."""
    profile = steering_profile_get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if profile.get("tenant_id") is not None and profile["tenant_id"] != tenant_context.tenant_id:
        raise HTTPException(status_code=404, detail="profile not found")
    strength = body.get("strength")
    if strength is not None:
        strength = float(strength)
    target = body.get("target") if isinstance(body.get("target"), dict) else None
    prompt_fragments = body.get("prompt_fragments") if isinstance(body.get("prompt_fragments"), list) else None
    classifier_thresholds = body.get("classifier_thresholds") if isinstance(body.get("classifier_thresholds"), dict) else None
    ok = steering_profile_update(
        profile_id,
        strength=strength,
        target=target,
        prompt_fragments=prompt_fragments,
        classifier_thresholds=classifier_thresholds,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="profile not found")
    return steering_profile_get(profile_id) or {}


@router.delete("/profiles/{profile_id}")
def delete_profile(
    profile_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Delete a steering profile. Must belong to tenant or be global."""
    profile = steering_profile_get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if profile.get("tenant_id") is not None and profile["tenant_id"] != tenant_context.tenant_id:
        raise HTTPException(status_code=404, detail="profile not found")
    ok = steering_profile_delete(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"ok": True, "profile_id": profile_id}


@router.get("/defaults")
def get_defaults(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get tenant default steering profile ids."""
    profile_ids = get_tenant_default_profile_ids(tenant_context.tenant_id)
    return {"profile_ids": profile_ids}


@router.put("/defaults")
def set_defaults(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Set tenant default steering profile ids. Body: { \"profile_ids\": [\"id1\", \"id2\"] }."""
    profile_ids = body.get("profile_ids")
    if not isinstance(profile_ids, list):
        raise HTTPException(status_code=400, detail="profile_ids array required")
    profile_ids = [str(p).strip() for p in profile_ids if p]
    set_tenant_default_profile_ids(tenant_context.tenant_id, profile_ids)
    return {"profile_ids": profile_ids}


@router.get("/chats/{chat_id}")
def get_chat_steering(
    chat_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get per-chat steering profile override. Returns profile_ids or null if not set."""
    profile_ids = get_chat_steering_profile_ids(tenant_context.tenant_id, chat_id)
    return {"chat_id": chat_id, "profile_ids": profile_ids}


@router.put("/chats/{chat_id}")
def set_chat_steering(
    chat_id: str,
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Set per-chat steering override. Body: { \"profile_ids\": [\"id1\"] } or null to clear."""
    profile_ids = body.get("profile_ids")
    if profile_ids is not None and not isinstance(profile_ids, list):
        raise HTTPException(status_code=400, detail="profile_ids must be array or null")
    if profile_ids is not None:
        profile_ids = [str(p).strip() for p in profile_ids if p]
    set_chat_steering_profile_ids(tenant_context.tenant_id, chat_id, profile_ids)
    return {"chat_id": chat_id, "profile_ids": profile_ids}


@router.get("/resolve")
def resolve_profiles(
    tenant_context: TenantContext = Depends(get_tenant_context),
    chat_id: Optional[str] = None,
    run_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve active steering profiles for tenant/chat (for debugging). run_override as comma-separated profile_ids."""
    override_list = None
    if run_override:
        override_list = [p.strip() for p in run_override.split(",") if p.strip()]
    resolved = resolve_steering_profiles(
        tenant_context.tenant_id,
        chat_id=chat_id,
        run_override=override_list,
    )
    return {"profiles": resolved}
