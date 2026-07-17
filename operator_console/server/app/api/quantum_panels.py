"""Quantum operator visibility panels API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.quantum_panels_service import (
    approve_correction,
    escalate_correction,
    get_entanglement_graph,
    get_noise_profile,
    get_noise_profiles,
    get_pair_decomposition,
    get_spectrum_emitter,
    get_spectrum_emitters,
    get_spectrum_snapshot,
    get_syndrome_dashboard,
    reject_correction,
    seed_quantum_demo,
    seed_spectrum_demo,
)

router = APIRouter()


class SeedDemoBody(BaseModel):
    fingerprint_id: str = "fp_quantum_demo"


class RejectBody(BaseModel):
    rationale: str = ""
    actor_id: str = "operator"


@router.post("/seed-demo")
def seed_demo(body: SeedDemoBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    return seed_quantum_demo(fingerprint_id=body.fingerprint_id)


@router.get("/entanglement/graph")
def entanglement_graph(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_entanglement_graph()


@router.get("/entanglement/pairs/{pair_id}")
def entanglement_pair(pair_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = get_pair_decomposition(pair_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.get("/noise/profiles")
def noise_profiles(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_noise_profiles()


@router.get("/noise/profiles/{entity_id}")
def noise_profile(entity_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = get_noise_profile(entity_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.get("/syndrome/dashboard")
def syndrome_dashboard(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_syndrome_dashboard()


@router.post("/syndrome/corrections/{correction_id}/approve")
def syndrome_approve(correction_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = approve_correction(correction_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.post("/syndrome/corrections/{correction_id}/reject")
def syndrome_reject(correction_id: str, body: RejectBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = reject_correction(correction_id, actor_id=body.actor_id, rationale=body.rationale)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.post("/syndrome/corrections/{correction_id}/escalate")
def syndrome_escalate(correction_id: str, body: RejectBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = escalate_correction(correction_id, actor_id=body.actor_id, rationale=body.rationale)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


@router.post("/spectrum/seed-demo")
def spectrum_seed_demo(_=Depends(require_api_key)) -> Dict[str, Any]:
    result = seed_spectrum_demo()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "seed_failed"))
    return result


@router.get("/spectrum/snapshot")
def spectrum_snapshot(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_spectrum_snapshot()


@router.get("/spectrum/emitters")
def spectrum_emitters(limit: int = 20, _=Depends(require_api_key)) -> Dict[str, Any]:
    return get_spectrum_emitters(limit=limit)


@router.get("/spectrum/emitters/{emitter_id}")
def spectrum_emitter(emitter_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    return get_spectrum_emitter(emitter_id)
