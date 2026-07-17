from fastapi import APIRouter, Depends, HTTPException
from ..core.auth import require_api_key
from ..services.analytics_service import get_analytics
from ..services.run_index_db import get_run

router = APIRouter()


@router.get("/{run_id}/analytics")
def run_analytics(run_id: str, _=Depends(require_api_key)):
    """GET run analytics: budget_used, counts, event_counts, node_summary."""
    if not get_run(run_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    out = get_analytics(run_id)
    if not out.get("ok"):
        raise HTTPException(status_code=404 if out.get("error", {}).get("code") == "NOT_FOUND" else 500, detail=out.get("error"))
    return out
