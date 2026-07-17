"""Quantum-2 staged activation operator API."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.quantum2_activation_service import (
    activation_history,
    activation_state,
    disable,
    divergence_review,
    enable_shadow,
    flip_fingerprint_codec_live,
    flip_shadow_first_live,
    go_no_go_state,
    live_activation_summary,
    production_divergence_report,
    production_validation_status,
    promote_live,
    run_production_validation,
    run_shadow_workloads,
)

router = APIRouter()


class ActivationActionBody(BaseModel):
    actor_id: str = "operator"
    rationale: str = ""


class PromoteLiveBody(ActivationActionBody):
    sign_off: bool = False


@router.get("/activation/state")
def get_state(_=Depends(require_api_key)) -> Dict[str, Any]:
    return activation_state()


@router.get("/activation/history")
def get_history(_=Depends(require_api_key)) -> Dict[str, Any]:
    return activation_history()


@router.get("/activation/divergence/{component}")
def get_divergence(component: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = divergence_review(component)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "invalid_component"))
    return result


@router.post("/activation/modules/{component}/enable-shadow")
def post_enable_shadow(
    component: str,
    body: ActivationActionBody,
    _=Depends(require_api_key),
) -> Dict[str, Any]:
    result = enable_shadow(component, actor_id=body.actor_id, rationale=body.rationale)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "enable_shadow_failed"))
    return result


@router.post("/activation/modules/{component}/promote-live")
def post_promote_live(
    component: str,
    body: PromoteLiveBody,
    _=Depends(require_api_key),
) -> Dict[str, Any]:
    result = promote_live(
        component,
        actor_id=body.actor_id,
        rationale=body.rationale,
        sign_off=body.sign_off,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "promote_live_failed"))
    return result


@router.post("/activation/modules/{component}/disable")
def post_disable(
    component: str,
    body: ActivationActionBody,
    _=Depends(require_api_key),
) -> Dict[str, Any]:
    result = disable(component, actor_id=body.actor_id, rationale=body.rationale)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "disable_failed"))
    return result


@router.post("/activation/run-shadow-workloads")
def post_run_shadow_workloads(_=Depends(require_api_key)) -> Dict[str, Any]:
    return run_shadow_workloads()


@router.get("/activation/go-no-go")
def get_go_no_go(_=Depends(require_api_key)) -> Dict[str, Any]:
    return go_no_go_state()


@router.post("/activation/flip-codec-live")
def post_flip_codec_live(body: ActivationActionBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = flip_fingerprint_codec_live(actor_id=body.actor_id, rationale=body.rationale)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "flip_failed"))
    return result


@router.post("/activation/flip-shadow-first-live")
def post_flip_shadow_first_live(body: ActivationActionBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = flip_shadow_first_live(actor_id=body.actor_id, rationale=body.rationale)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "flip_failed"))
    return result


@router.get("/activation/live-summary")
def get_live_summary(_=Depends(require_api_key)) -> Dict[str, Any]:
    return live_activation_summary()


@router.post("/validation/run")
def post_run_production_validation(_=Depends(require_api_key)) -> Dict[str, Any]:
    result = run_production_validation()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("stage") or "validation_failed")
    return result


@router.get("/validation/status")
def get_production_validation_status(_=Depends(require_api_key)) -> Dict[str, Any]:
    return production_validation_status()


@router.get("/validation/divergence-report")
def get_production_divergence_report(_=Depends(require_api_key)) -> Dict[str, Any]:
    return production_divergence_report()
