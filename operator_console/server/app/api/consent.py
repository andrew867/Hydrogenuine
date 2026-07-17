"""Consent surface operator API (G15)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..core.consent import require_consent_surface_enabled, require_recognition_consent
from ..services.consent_service import (
    get_consent_status,
    get_ledger_page,
    grant_consent,
    revoke_consent,
    seed_demo_grants,
)

router = APIRouter()


class GrantBody(BaseModel):
    subject_id: str
    consent_class: str
    purpose: str
    granted_by: str = "operator"
    expires_at: Optional[str] = None
    proof_bundle_ref: Optional[str] = None


class RevokeBody(BaseModel):
    record_id: str
    subject_id: str
    revoked_by: str = "operator"


@router.get("/status")
def consent_status(
    subject_id: str = Query(...),
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return get_consent_status(subject_id)


@router.post("/grant")
def consent_grant(
    body: GrantBody,
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return grant_consent(
        subject_id=body.subject_id,
        consent_class=body.consent_class,
        purpose=body.purpose,
        granted_by=body.granted_by,
        expires_at=body.expires_at,
        proof_bundle_ref=body.proof_bundle_ref,
    )


@router.post("/revoke")
def consent_revoke(
    body: RevokeBody,
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return revoke_consent(
        record_id=body.record_id,
        subject_id=body.subject_id,
        revoked_by=body.revoked_by,
    )


@router.get("/ledger")
def consent_ledger(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return get_ledger_page(offset=offset, limit=limit)


@router.post("/seed-demo")
def consent_seed_demo(
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return seed_demo_grants()


@router.get("/recognition-probe")
def recognition_probe(
    subject_id: str = Query(...),
    _auth=Depends(require_api_key),
    effective: str = Depends(require_recognition_consent),
) -> Dict[str, Any]:
    """Guarded probe route for integration tests (user_recognition=True semantics)."""
    return {"ok": True, "subject_id": subject_id, "effective_class": effective}
