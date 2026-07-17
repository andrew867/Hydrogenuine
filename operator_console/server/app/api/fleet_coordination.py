"""Fleet coordination operator panel API (Phase 10)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.fleet_coordination_service import (
    get_fleet_snapshot,
    run_mesh_cross_host_proof,
    seed_fleet_demo,
    trigger_zone_halt,
)

router = APIRouter()


class HaltZoneBody(BaseModel):
    reason: str = "operator_halt"


@router.post("/seed-demo")
def seed_demo(_=Depends(require_api_key)) -> Dict[str, Any]:
    return seed_fleet_demo()


@router.get("/snapshot")
def snapshot(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_fleet_snapshot()


@router.post("/mesh/cross-host-proof")
def mesh_proof(_=Depends(require_api_key)) -> Dict[str, Any]:
    result = run_mesh_cross_host_proof()
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail="cross_host_proof_failed")
    return result


@router.post("/zones/{zone_id}/halt")
def halt_zone(zone_id: str, body: HaltZoneBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = trigger_zone_halt(zone_id, reason=body.reason)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "halt_failed"))
    return result
