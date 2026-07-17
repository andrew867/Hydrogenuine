"""Quantum-2 structure track operator API (sum-rule ledger + conservation)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.quantum2_panels_service import (
    allocate_sum_rule,
    audit_sum_rule,
    estimate_sum_rule_capacity,
    get_sum_rule_state,
    transfer_sum_rule,
)

router = APIRouter()


class CapacityBody(BaseModel):
    entity_count: int = Field(..., ge=1)
    token_budget: float = Field(..., gt=0)
    latency_ceiling_ms: float = Field(..., gt=0)


class AllocateBody(BaseModel):
    task_risk_profile: Dict[str, float] = Field(default_factory=dict)


class TransferBody(BaseModel):
    from_class: str
    to_class: str
    amount: float = Field(..., gt=0)
    actor_id: str = "operator"
    rationale: str = ""


class AuditBody(BaseModel):
    telemetry: Dict[str, Any] = Field(default_factory=dict)


@router.get("/sum-rule/state")
def sum_rule_state(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_sum_rule_state()


@router.post("/sum-rule/capacity")
def sum_rule_capacity(body: CapacityBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    return estimate_sum_rule_capacity(
        entity_count=body.entity_count,
        token_budget=body.token_budget,
        latency_ceiling_ms=body.latency_ceiling_ms,
    )


@router.post("/sum-rule/allocate")
def sum_rule_allocate(body: AllocateBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = allocate_sum_rule(body.task_risk_profile)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "allocate_failed"))
    return result


@router.post("/sum-rule/transfer")
def sum_rule_transfer(body: TransferBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = transfer_sum_rule(
        from_class=body.from_class,
        to_class=body.to_class,
        amount=body.amount,
        actor_id=body.actor_id,
        rationale=body.rationale,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "transfer_failed"))
    return result


@router.post("/sum-rule/audit")
def sum_rule_audit(body: AuditBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    return audit_sum_rule(body.telemetry)
