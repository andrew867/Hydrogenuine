"""Proof reconstruction operator API (P2-5)."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.proof_reconstruction_service import (
    get_reconstruction_dashboard,
    reconstruct_from_ids,
    seed_proof_reconstruction_demo,
)

router = APIRouter()


class ReconstructBody(BaseModel):
    proof_snapshot_ids: List[str] = Field(default_factory=list)


@router.post("/seed-demo")
def seed_demo(_=Depends(require_api_key)) -> Dict[str, Any]:
    return seed_proof_reconstruction_demo()


@router.get("/dashboard")
def dashboard(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_reconstruction_dashboard()


@router.post("/reconstruct")
def reconstruct(body: ReconstructBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    return reconstruct_from_ids(body.proof_snapshot_ids)
