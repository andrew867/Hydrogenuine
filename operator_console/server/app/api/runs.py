from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from ..core.auth import require_api_key, require_api_key_or_query
from ..services.run_ops import list_runs, get_run, resume_run, approve_run, deny_run
from ..services.run_index_db import get_run as get_run_row
from ..services.events_stream import stream_events
from ..services.runs_list_stream import stream_runs_list
from ..services.replay_ops import replay_run, cancel_run, cancel_stale_runs
from ..services.state_reader import read_state as get_state
from ..services.tool_trace import load_tool_trace
from ..services.launcher_service import _run_request
from ..services.lease_heartbeat import run_heartbeat
from ..services.swarm_tree import get_swarm_tree
from ..services.run_lineage import build_run_lineage_summary
from ..services.stream_tokens import mint_stream_token

router = APIRouter()


@router.get("/{run_id}/events/stream-token")
def events_stream_token(run_id: str, _=Depends(require_api_key)):
    """Mint a short-lived token for EventSource SSE (no Authorization header support)."""
    if not get_run_row(run_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    token = mint_stream_token(run_id)
    return {"token": token, "expires_in_sec": 120}


@router.get("/{run_id}/events/stream")
def events_stream(run_id: str, _=Depends(require_api_key_or_query)):
    """SSE stream tailing run_dir/events.jsonl (auth via Bearer or api_key query for EventSource)."""
    if not get_run_row(run_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "run not found"})
    return StreamingResponse(
        stream_events(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream")
async def runs_list_stream(limit: int = 200, _=Depends(require_api_key)):
    """SSE stream: emits runs.delta when the runs list snapshot changes."""
    return StreamingResponse(
        stream_runs_list(limit=limit),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("")
def runs(limit: int = 5000, _=Depends(require_api_key)):
    return list_runs(limit=limit)


@router.post("/cancel-stale")
def cancel_stale(stale_minutes: int = 0, _=Depends(require_api_key)):
    """Cancel active runs and gate-queue stubs. stale_minutes=0 cancels all active rows."""
    return cancel_stale_runs(stale_minutes=stale_minutes)


@router.get("/{run_id}/state")
def run_state(run_id: str, _=Depends(require_api_key)):
    """GET run state (state.json) for node table and run state."""
    return get_state(run_id)


@router.get("/{run_id}")
def run_detail(run_id: str, _=Depends(require_api_key)):
    return get_run(run_id)


@router.get("/{run_id}/tool-trace")
def tool_trace(run_id: str, limit: int = 200, _=Depends(require_api_key)):
    return load_tool_trace(run_id, limit=limit)


@router.get("/{run_id}/swarm")
def run_swarm_tree(run_id: str, _=Depends(require_api_key)):
    """L10: Swarm tree and run lineage for dashboard."""
    lineage = build_run_lineage_summary(run_id)
    lineage["swarm_tree"] = get_swarm_tree(run_id)
    return lineage


@router.get("/{run_id}/lineage")
def run_lineage(run_id: str, _=Depends(require_api_key)):
    """Return a navigable lineage summary for workflow/run/swarm/chat relations."""
    return build_run_lineage_summary(run_id)


@router.post("/{run_id}/resume")
def resume(run_id: str, _=Depends(require_api_key)):
    return resume_run(run_id)


@router.post("/{run_id}/approve")
def approve(run_id: str, _=Depends(require_api_key)):
    """Approve a run that is pending_approval (gate-blocked); scheduler will launch it."""
    out = approve_run(run_id)
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", {"code": "APPROVE_FAILED", "message": "approve failed"}))
    return out


@router.post("/{run_id}/deny")
def deny(run_id: str, body: dict | None = None, _=Depends(require_api_key)):
    """Deny a run that is pending_approval; run is marked blocked."""
    reason = (body or {}).get("reason") if isinstance(body, dict) else None
    out = deny_run(run_id, reason=reason)
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", {"code": "DENY_FAILED", "message": "deny failed"}))
    return out


@router.post("/{run_id}/replay")
def replay(run_id: str, _=Depends(require_api_key)):
    out = replay_run(run_id)
    if not out.get("ok") and (out.get("error") or {}).get("code") == "HG_CORE_REQUIRED":
        raise HTTPException(status_code=503, detail=out["error"])
    return out


@router.post("/request")
def run_request(body: dict, _=Depends(require_api_key)):
    """L10: Request a new DAG run. Body: workflow_id, optional tenant_id, actor_id, correlation_id, resolved_inputs. Returns { ok, run_id }."""
    workflow_id = (body.get("workflow_id") or "").strip()
    if not workflow_id:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "workflow_id is required"})
    result = _run_request(
        workflow_id=workflow_id,
        tenant_id=(body.get("tenant_id") or "default").strip(),
        actor_id=(body.get("actor_id") or "api").strip(),
        correlation_id=(body.get("correlation_id") or "").strip() or None,
        resolved_inputs=body.get("resolved_inputs") if isinstance(body.get("resolved_inputs"), dict) else None,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"code": "LAUNCH_FAILED", "message": result.get("error", "launch failed")})
    return result


@router.post("/{run_id}/heartbeat")
def heartbeat(run_id: str, body: dict, _=Depends(require_api_key)):
    """L10: Run lease heartbeat. Body: lease_id, worker_id, seq (monotonic)."""
    lease_id = (body.get("lease_id") or "").strip()
    worker_id = (body.get("worker_id") or "").strip()
    seq = body.get("seq")
    if not lease_id or not worker_id or seq is None:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "lease_id, worker_id, seq required"})
    try:
        seq = int(seq)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "seq must be integer"})
    result = run_heartbeat(run_id=run_id, lease_id=lease_id, worker_id=worker_id, seq=seq)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"code": "HEARTBEAT_FAILED", "message": result.get("error", "heartbeat failed")})
    return result


@router.post("/{run_id}/cancel")
def cancel(run_id: str, _=Depends(require_api_key)):
    return cancel_run(run_id)
