"""
Layer 8 Phase 4: Operator console API for representation interpretability.
"""
from fastapi import APIRouter, Depends, Query
from ..core.auth import require_api_key
from ..services.repr_interp_service import get_repr_interp_results, get_proof_path_for_decision

router = APIRouter()


@router.get("/results")
def repr_interp_results(
    run_id: str | None = Query(None, description="Filter by run_id"),
    decision_id: str | None = Query(None, description="Filter by decision_id"),
    node_id: str | None = Query(None, description="Filter by node_id"),
    limit: int = Query(100, ge=1, le=500),
    _=Depends(require_api_key),
):
    """GET representation interpretability inspection results (optional filters: run_id, decision_id, node_id)."""
    return get_repr_interp_results(run_id=run_id, decision_id=decision_id, node_id=node_id, limit=limit)


@router.get("/decisions/{decision_id}/proof-path")
def decision_proof_path(decision_id: str, _=Depends(require_api_key)):
    """GET full proof path for a decision (includes representation_inspection_result when present)."""
    return get_proof_path_for_decision(decision_id)
