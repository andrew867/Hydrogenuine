from fastapi import APIRouter, Depends, Query
from ..core.auth import require_api_key
from ..services.ownership_service import (
    get_ownership_chain,
    get_ownership_edges,
    get_ownership_events,
    search_ownership_events,
    get_ownership_availability,
)

router = APIRouter()


@router.get("/{run_id}/ownership/chain")
def ownership_chain(
    run_id: str,
    task_id: str | None = Query(None),
    _=Depends(require_api_key),
):
    return get_ownership_chain(run_id, task_id=task_id)


@router.get("/{run_id}/ownership/edges")
def ownership_edges(
    run_id: str,
    task_id: str | None = Query(None),
    _=Depends(require_api_key),
):
    return get_ownership_edges(run_id, task_id=task_id)


@router.get("/{run_id}/ownership/events")
def ownership_events(
    run_id: str,
    task_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    _=Depends(require_api_key),
):
    return get_ownership_events(run_id, task_id=task_id, limit=limit)


@router.get("/{run_id}/ownership/search")
def ownership_search(
    run_id: str,
    q: str = Query("", alias="q"),
    task_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    _=Depends(require_api_key),
):
    return search_ownership_events(run_id, q, task_id=task_id, limit=limit)


@router.get("/{run_id}/ownership/availability")
def ownership_availability(run_id: str, _=Depends(require_api_key)):
    return get_ownership_availability(run_id)
