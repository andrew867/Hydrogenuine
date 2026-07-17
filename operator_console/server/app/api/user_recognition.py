"""User cognitive recognition API (G16 / telex)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..core.consent import require_consent_surface_enabled
from ..services.user_recognition_service import (
    analyze_user_recognition,
    get_user_recognition_status,
    list_kinship_templates,
    seed_user_recognition_demo,
)

router = APIRouter()


class AnalyzeBody(BaseModel):
    subject_id: str
    interaction: Dict[str, Any] = Field(default_factory=dict)
    purpose: str = "operator_panel"
    proof_bundle_ref: Optional[str] = None


@router.get("/status")
def user_recognition_status(
    subject_id: str = Query(...),
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return get_user_recognition_status(subject_id)


@router.post("/analyze")
def user_recognition_analyze(
    body: AnalyzeBody,
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return analyze_user_recognition(
        subject_id=body.subject_id,
        interaction=body.interaction,
        purpose=body.purpose,
        proof_bundle_ref=body.proof_bundle_ref,
    )


@router.get("/templates")
def user_recognition_templates(
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return list_kinship_templates()


@router.post("/seed-demo")
def user_recognition_seed_demo(
    _auth=Depends(require_api_key),
    _surface=Depends(require_consent_surface_enabled),
) -> Dict[str, Any]:
    return seed_user_recognition_demo()
