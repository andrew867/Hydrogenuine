"""Advanced Wave 2 models operator panel API."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import require_api_key
from ..services.advanced_models_service import (
    get_model_detail,
    get_models_dashboard,
    seed_advanced_models_demo,
)

router = APIRouter()


@router.post("/seed-demo")
def seed_demo(_=Depends(require_api_key)) -> Dict[str, Any]:
    return seed_advanced_models_demo()


@router.get("/dashboard")
def dashboard(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_models_dashboard()


@router.get("/models/{model_id}")
def model_detail(model_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = get_model_detail(model_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result
