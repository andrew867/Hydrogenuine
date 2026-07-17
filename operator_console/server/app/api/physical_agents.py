"""Physical agents operator panel API."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.physical_agents_service import (
    evaluate_command,
    get_physical_agent,
    halt_robot,
    list_physical_agents,
    resume_robot,
    seed_physical_demo,
)

router = APIRouter()


class EvaluateBody(BaseModel):
    action: str = "read_sensor"
    operator_ack: bool = False


class HaltBody(BaseModel):
    reason: str = "operator_halt"


@router.post("/seed-demo")
def seed_demo(_=Depends(require_api_key)) -> Dict[str, Any]:
    return seed_physical_demo()


@router.get("/agents")
def agents(_=Depends(require_api_key)) -> Dict[str, Any]:
    return list_physical_agents()


@router.get("/agents/{robot_id}")
def agent(robot_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = get_physical_agent(robot_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.post("/agents/{robot_id}/halt")
def halt(robot_id: str, body: HaltBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = halt_robot(robot_id, reason=body.reason)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.post("/agents/{robot_id}/resume")
def resume(robot_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = resume_robot(robot_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "resume_failed"))
    return result


@router.post("/agents/{robot_id}/evaluate")
def evaluate(robot_id: str, body: EvaluateBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = evaluate_command(robot_id, body.action, operator_ack=body.operator_ack)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result
