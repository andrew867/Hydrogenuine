"""
Pack 23: Utility API — elicitation runs, fits, drifts, summary. Analytics: tag_means, trends, incidents, report.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from hg_core.tenancy.context import TenantContext
from hg_gateway.auth import get_tenant_context, verify_api_key

router = APIRouter(prefix="/utility", tags=["utility"], dependencies=[Depends(verify_api_key)])

# In-memory store for Phase 3; proof runner or jobs can populate. Key: (tenant_id, model_id, persona_id) or similar.
_utility_fits: List[Dict[str, Any]] = []
_utility_drifts: List[Dict[str, Any]] = []


@router.post("/elicitation/run")
def post_utility_elicitation_run(
    tenant_context: TenantContext = Depends(get_tenant_context),
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Start utility elicitation run. Body: dataset_version, suite_id?, persona_ids?, model_id, budget_K, template_id, mode."""
    return {
        "run_id": "run_placeholder",
        "status": "accepted",
        "message": "Use proof runner for full elicitation; API stores runs when implemented.",
    }


@router.get("/runs/{run_id}")
def get_utility_run(
    run_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get elicitation run status."""
    return {"run_id": run_id, "status": "unknown", "comparisons_count": 0}


@router.get("/fits")
def get_utility_fits(
    tenant_context: TenantContext = Depends(get_tenant_context),
    persona_id: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    dataset_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """List utility fits for tenant."""
    tenant_id = tenant_context.tenant_id
    fits = [f for f in _utility_fits if f.get("tenant_id") == tenant_id]
    return {"tenant_id": tenant_id, "fits": fits}


@router.get("/drifts")
def get_utility_drifts(
    tenant_context: TenantContext = Depends(get_tenant_context),
    persona_id: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    window: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """List utility drifts for tenant."""
    tenant_id = tenant_context.tenant_id
    drifts = [d for d in _utility_drifts if d.get("tenant_id") == tenant_id]
    return {"tenant_id": tenant_id, "drifts": drifts}


@router.get("/summary")
def get_utility_summary(
    tenant_context: TenantContext = Depends(get_tenant_context),
    persona_id: Optional[str] = Query(None),
    window: Optional[str] = Query("7d"),
) -> Dict[str, Any]:
    """Utility summary: fit count, drift count, last run."""
    tenant_id = tenant_context.tenant_id
    fits = [f for f in _utility_fits if f.get("tenant_id") == tenant_id]
    drifts = [d for d in _utility_drifts if d.get("tenant_id") == tenant_id]
    return {
        "tenant_id": tenant_id,
        "fits_count": len(fits),
        "drifts_count": len(drifts),
        "window": window or "7d",
    }
