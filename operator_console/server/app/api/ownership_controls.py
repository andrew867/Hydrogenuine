"""Ownership API: conflict detection and handoff events."""

from pathlib import Path
import os
import time

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import require_api_key
from ..services.run_index_db import get_run, list_runs

router = APIRouter()
_OWNERSHIP_CONFLICT_CACHE: dict[str, object] = {"expires_at": 0.0, "value": None}
_OWNERSHIP_HANDOFF_CACHE: dict[str, object] = {"expires_at": 0.0, "key": None, "value": None}

HANDOFF_TYPES = ("offer_ownership", "accept_ownership", "decline_ownership", "release_ownership")


def _ownership_db_path(run_id: str) -> Path | None:
    r = get_run(run_id)
    if not r or not r.get("run_dir"):
        return None
    return Path(r["run_dir"]) / "ownership.db"


@router.get("/conflicts")
def get_conflicts(_=Depends(require_api_key)):
    """List runs/tasks with contested ownership state."""
    if (os.environ.get("HG_ENABLE_OWNERSHIP_SCAN") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return {"ok": True, "conflicts": []}
    now = time.time()
    cached = _OWNERSHIP_CONFLICT_CACHE.get("value")
    if float(_OWNERSHIP_CONFLICT_CACHE.get("expires_at") or 0.0) > now and isinstance(cached, dict):
        return cached
    try:
        from hg_core.ownership import ownership_db
        conflicts = []
        runs = list_runs(limit=5)
        deadline = now + 3.0
        for r in runs:
            if time.time() >= deadline:
                break
            run_id = r["run_id"]
            db_path = _ownership_db_path(run_id)
            if not db_path or not db_path.exists():
                continue
            ownership_db.init_ownership_schema(str(db_path))
            rows = ownership_db.state_list_contested(str(db_path), run_id)
            for row in rows:
                conflicts.append({
                    "run_id": run_id,
                    "task_id": row.get("task_id"),
                    "state": row.get("state", "contested"),
                    "contested_claims": row.get("contested_claims"),
                })
        result = {"ok": True, "conflicts": conflicts}
        _OWNERSHIP_CONFLICT_CACHE.update({"expires_at": now + 30.0, "value": result})
        return result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/handoffs")
def get_handoffs(limit: int = 100, _=Depends(require_api_key)):
    """List recent handoff events (offer/accept/decline/release) across runs."""
    if (os.environ.get("HG_ENABLE_OWNERSHIP_SCAN") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return {"ok": True, "events": []}
    limit = max(1, min(limit, 200))
    cache_key = limit
    now = time.time()
    cached = _OWNERSHIP_HANDOFF_CACHE.get("value")
    if _OWNERSHIP_HANDOFF_CACHE.get("key") == cache_key and float(_OWNERSHIP_HANDOFF_CACHE.get("expires_at") or 0.0) > now and isinstance(cached, dict):
        return cached
    try:
        from hg_core.ownership import ownership_db
        events = []
        runs = list_runs(limit=5)
        deadline = now + 3.0
        for r in runs:
            if time.time() >= deadline:
                break
            run_id = r["run_id"]
            db_path = _ownership_db_path(run_id)
            if not db_path or not db_path.exists():
                continue
            ownership_db.init_ownership_schema(str(db_path))
            rows = ownership_db.ledger_list_events(str(db_path), run_id, task_id=None, limit=50)
            for row in rows:
                if row.get("type") in HANDOFF_TYPES:
                    events.append({
                        "run_id": run_id,
                        "task_id": row.get("task_id"),
                        "type": row.get("type"),
                        "actor": row.get("actor"),
                        "ts": row.get("ts"),
                    })
        events.sort(key=lambda x: (x.get("ts") or 0), reverse=True)
        result = {"ok": True, "events": events[:limit]}
        _OWNERSHIP_HANDOFF_CACHE.update({"expires_at": now + 30.0, "key": cache_key, "value": result})
        return result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
