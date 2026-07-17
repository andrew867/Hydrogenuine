"""User cognitive recognition routes (G15 consent + G16 telex)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from hg_gateway.auth import verify_api_key
from hg_gateway.consent import require_recognition_consent

router = APIRouter(
    prefix="/recognition",
    tags=["recognition"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/probe")
def recognition_probe(effective: str = Depends(require_recognition_consent)) -> Dict[str, Any]:
    """Probe route for user-targeted recognition consent enforcement (G15 test hook)."""
    return {"ok": True, "effective_class": effective}


class AnalyzeBody(BaseModel):
    subject_id: str
    interaction: Dict[str, Any] = Field(default_factory=dict)
    purpose: str = "gateway"
    proof_bundle_ref: Optional[str] = None


@router.post("/analyze")
def recognition_analyze(
    body: AnalyzeBody,
    effective: str = Depends(require_recognition_consent),
) -> Dict[str, Any]:
    """Consent-gated user cognitive recognition (G16)."""
    from hg_core.repr_interp.user_recognition import is_user_recognition_enabled, recognize_user

    if not is_user_recognition_enabled():
        return {"ok": False, "error": "user_recognition_disabled"}
    if body.subject_id:
        pass
    return recognize_user(
        subject_id=body.subject_id,
        interaction=body.interaction,
        purpose=body.purpose,
        proof_bundle_ref=body.proof_bundle_ref,
    )


@router.get("/status")
def recognition_status_route(subject_id: str = Query(...)) -> Dict[str, Any]:
    from hg_core.repr_interp.user_recognition import recognition_status

    return recognition_status(subject_id=subject_id)
