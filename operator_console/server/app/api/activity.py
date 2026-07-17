from fastapi import APIRouter, Depends, Query
from ..core.auth import require_api_key
from ..services.activity_service import get_recent_activity

router = APIRouter()


def _activity_response(
    limit_runs: int = Query(10, ge=1, le=50),
    limit_decisions: int = Query(20, ge=1, le=100),
    entity_id: str | None = Query(None),
    chat_id: str | None = Query(None),
    run_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    view: str = Query("compact"),
    _=Depends(require_api_key),
):
    """Recent runs, recent decisions across entities, and overseer summary."""
    data = get_recent_activity(
        limit_runs=limit_runs,
        limit_decisions=limit_decisions,
        entity_id=entity_id,
        chat_id=chat_id,
        run_id=run_id,
        workflow_id=workflow_id,
        projection_view=view,
    )
    return {"ok": True, **data}


@router.get("")
def activity(
    limit_runs: int = Query(10, ge=1, le=50),
    limit_decisions: int = Query(20, ge=1, le=100),
    entity_id: str | None = Query(None),
    chat_id: str | None = Query(None),
    run_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    view: str = Query("compact"),
    _=Depends(require_api_key),
):
    return _activity_response(
        limit_runs=limit_runs,
        limit_decisions=limit_decisions,
        entity_id=entity_id,
        chat_id=chat_id,
        run_id=run_id,
        workflow_id=workflow_id,
        view=view,
    )


@router.get("/recent")
def recent_activity(
    limit_runs: int = Query(10, ge=1, le=50),
    limit_decisions: int = Query(20, ge=1, le=100),
    entity_id: str | None = Query(None),
    chat_id: str | None = Query(None),
    run_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    view: str = Query("compact"),
    _=Depends(require_api_key),
):
    return _activity_response(
        limit_runs=limit_runs,
        limit_decisions=limit_decisions,
        entity_id=entity_id,
        chat_id=chat_id,
        run_id=run_id,
        workflow_id=workflow_id,
        view=view,
    )


@router.get("/projection")
def activity_projection(
    limit_runs: int = Query(10, ge=1, le=50),
    limit_decisions: int = Query(20, ge=1, le=100),
    entity_id: str | None = Query(None),
    chat_id: str | None = Query(None),
    run_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    view: str = Query("compact"),
    _=Depends(require_api_key),
):
    return _activity_response(
        limit_runs=limit_runs,
        limit_decisions=limit_decisions,
        entity_id=entity_id,
        chat_id=chat_id,
        run_id=run_id,
        workflow_id=workflow_id,
        view=view,
    )
