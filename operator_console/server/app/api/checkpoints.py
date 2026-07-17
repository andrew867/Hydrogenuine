from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..core.auth import require_api_key
from ..services.checkpoint_store import list_checkpoints as list_cps, approve as approve_cp, deny as deny_cp

router = APIRouter()


class Decision(BaseModel):
    comment: str | None = None


@router.get("/{run_id}/checkpoints")
def list_checkpoints(run_id: str, _=Depends(require_api_key)):
    try:
        checkpoints = list_cps(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    return {"ok": True, "run_id": run_id, "checkpoints": checkpoints}


@router.post("/{run_id}/checkpoints/{checkpoint_id}/approve")
def approve(run_id: str, checkpoint_id: str, payload: Decision, _=Depends(require_api_key)):
    try:
        result = approve_cp(run_id, checkpoint_id, payload.comment)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID", "message": str(e)})


@router.post("/{run_id}/checkpoints/{checkpoint_id}/deny")
def deny(run_id: str, checkpoint_id: str, payload: Decision, _=Depends(require_api_key)):
    try:
        result = deny_cp(run_id, checkpoint_id, payload.comment)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID", "message": str(e)})
