from fastapi import APIRouter, Depends, HTTPException
from ..core.auth import require_api_key
from ..services.state_history_store import list_snapshots, load_snapshot, fork_from_snapshot

router = APIRouter()

@router.get("/{run_id}/snapshots")
def snapshots(run_id: str, _=Depends(require_api_key)):
    try:
        rows = list_snapshots(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    return {"ok": True, "run_id": run_id, "snapshots": rows}

@router.get("/{run_id}/snapshots/{seq}")
def snapshot(run_id: str, seq: int, _=Depends(require_api_key)):
    try:
        state = load_snapshot(run_id, seq)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    if state is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"snapshot {seq} not found"})
    return {"ok": True, "run_id": run_id, "seq": seq, "state": state}

@router.post("/{run_id}/fork/{seq}")
def fork(run_id: str, seq: int, _=Depends(require_api_key)):
    out = fork_from_snapshot(run_id, seq)
    if out.get("ok"):
        return out
    err = out.get("error") or {}
    code = err.get("code")
    status_code = 500
    if code == "NOT_FOUND":
        status_code = 404
    elif code in ("NOT_IMPLEMENTED", "HG_CORE_REQUIRED"):
        status_code = 503
    raise HTTPException(status_code=status_code, detail=err or {"code": "ERROR", "message": "fork failed"})
