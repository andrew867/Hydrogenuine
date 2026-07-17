"""Mediator registry operator API (Q2.5)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.mediator_panels_service import get_mediator_catalog, probe_mediator, register_mediator

router = APIRouter()


class RegisterMediatorBody(BaseModel):
    mediator_id: str
    latent_state_class: str
    coupling_mechanism: str
    cost_profile: Dict[str, float] = Field(default_factory=dict)
    surfacing_policy: str
    consent_constraints: Dict[str, Any] = Field(default_factory=dict)
    target_scope: str = "entity"
    rate_limit_per_hour: int = 12


class ProbeBody(BaseModel):
    entity_id: str
    latent_state_class: str
    context: Dict[str, Any] = Field(default_factory=dict)


@router.get("/catalog")
def catalog(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_mediator_catalog()


@router.post("/register")
def register(body: RegisterMediatorBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = register_mediator(body.model_dump())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "register_failed"))
    return result


@router.post("/probe")
def probe(body: ProbeBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = probe_mediator(
        entity_id=body.entity_id,
        latent_state_class=body.latent_state_class,
        context=body.context,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "probe_failed"))
    return result
