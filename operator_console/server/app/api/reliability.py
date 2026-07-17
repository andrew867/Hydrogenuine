"""Reliability API: failure classes, retry policy, circuit breakers, incident queue, and budget summary."""

from pathlib import Path
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key

router = APIRouter()
_BUDGET_CACHE: dict[str, object] = {"expires_at": 0.0, "key": None, "value": None}


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return Path(get_workspace_root())
    except Exception:
        return None


@router.get("/failure-classes")
def get_failure_classes(_=Depends(require_api_key)):
    """List known failure classes."""
    try:
        from hg_core.task_graph.failure_classification import FAILURE_CLASSES
        return {"ok": True, "classes": list(FAILURE_CLASSES)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/retry-policy")
def get_retry_policy(class_name: str | None = None, _=Depends(require_api_key)):
    """Retry policy for all classes or one (query: class=optional)."""
    try:
        from hg_core.task_graph.retry_policy import get_retry_policy_for_class
        from hg_core.task_graph.failure_classification import FAILURE_CLASSES
        if class_name:
            policy = get_retry_policy_for_class(class_name)
            return {"ok": True, "policy": policy, "class": class_name}
        policies = {c: get_retry_policy_for_class(c) for c in FAILURE_CLASSES}
        return {"ok": True, "policies": policies}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


def _list_breakers(root: Path) -> list:
    from hg_core.task_graph.circuit_breaker import CIRCUIT_BREAKER_DIR, _load_state
    base = root / CIRCUIT_BREAKER_DIR
    if not base.exists():
        return []
    out = []
    for p in base.iterdir():
        if p.is_file() and p.suffix == ".json":
            state = _load_state(p)
            out.append({
                "workflow_id": p.stem,
                "destination": None,
                "failures": state.get("failures", 0),
                "tripped_at": state.get("tripped_at"),
                "tripped": bool(state.get("tripped_at")),
            })
        elif p.is_dir():
            for f in p.glob("*.json"):
                state = _load_state(f)
                out.append({
                    "workflow_id": p.name,
                    "destination": f.stem,
                    "failures": state.get("failures", 0),
                    "tripped_at": state.get("tripped_at"),
                    "tripped": bool(state.get("tripped_at")),
                })
    return out


@router.get("/breakers")
def list_breakers(_=Depends(require_api_key)):
    """List circuit breaker state per workflow (and per destination)."""
    root = _workspace_root()
    if not root:
        raise HTTPException(status_code=503, detail="workspace root not configured")
    try:
        breakers = _list_breakers(root)
        return {"ok": True, "breakers": breakers}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class ResetBreakerBody(BaseModel):
    workflow_id: str
    destination: str | None = None


@router.post("/breakers/reset")
def reset_breaker(body: ResetBreakerBody, _=Depends(require_api_key)):
    """Reset circuit breaker for (workflow_id, destination)."""
    root = _workspace_root()
    if not root:
        raise HTTPException(status_code=503, detail="workspace root not configured")
    try:
        from hg_core.task_graph.circuit_breaker import reset_breaker as cb_reset
        cb_reset(root, body.workflow_id, body.destination)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/incident-queue")
def list_incident_queue(task_id: str | None = None, _=Depends(require_api_key)):
    """List incident queue files, optionally filtered by task_id."""
    root = _workspace_root()
    if not root:
        raise HTTPException(status_code=503, detail="workspace root not configured")
    try:
        from hg_core.deadletter import list_deadletter_files, load_deadletter
        paths = list_deadletter_files(root, task_id=task_id)
        items = []
        for p in paths:
            try:
                payload = load_deadletter(p)
                items.append({
                    "path": str(p),
                    "task_id": payload.get("task_id"),
                    "run_id": payload.get("run_id"),
                    "written_at": payload.get("written_at"),
                })
            except Exception:
                items.append({"path": str(p), "task_id": None, "run_id": None, "written_at": None})
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/reconcile-run-index")
def reconcile_run_index(limit: int = 8000, _=Depends(require_api_key)):
    """Reconcile Postgres run index with on-disk summary.json artifacts."""
    try:
        from ..services.run_index_db import reconcile_runs_from_disk

        return reconcile_runs_from_disk(limit=max(100, min(limit, 20000)))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/budget-summary")
def get_budget_summary(recent_runs: int = 200, _=Depends(require_api_key)):
    """Aggregate budget_used across recent runs by workflow (graph_id)."""
    recent_runs = max(1, min(recent_runs, 5))
    cache_key = recent_runs
    now = time.time()
    if _BUDGET_CACHE.get("key") == cache_key and float(_BUDGET_CACHE.get("expires_at") or 0.0) > now:
        cached = _BUDGET_CACHE.get("value")
        if isinstance(cached, dict):
            return cached
    try:
        from ..services.run_index_db import list_runs
        runs = list_runs(limit=recent_runs)
    except Exception:
        return {"ok": True, "by_workflow": {}, "recent_runs": 0}
    by_workflow = {}
    for r in runs:
        wid = r.get("graph_id") or "unknown"
        if wid not in by_workflow:
            by_workflow[wid] = {"runs": 0, "total_budget_used": 0}
        by_workflow[wid]["runs"] += 1
        budget_used = r.get("budget_used")
        if isinstance(budget_used, (int, float)):
            by_workflow[wid]["total_budget_used"] += budget_used
    result = {"ok": True, "by_workflow": by_workflow, "recent_runs": len(runs)}
    _BUDGET_CACHE.update({"expires_at": now + 30.0, "key": cache_key, "value": result})
    return result
