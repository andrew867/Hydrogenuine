"""
Pack 25: Replay API — verify event/ledger chains for a run_id.
POST /v1/admin/replay/run {run_id, tenant_id?}; GET /v1/admin/replay/{run_id} returns report.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from hg_gateway.auth import require_admin
from hg_gateway.replay_engine import verify_run_replay


router = APIRouter(prefix="/admin/replay", tags=["admin-replay"], dependencies=[Depends(require_admin)])


@router.post("/run")
def admin_replay_run(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run replay verification for run_id. Body: { "run_id": str, "tenant_id"?: str }.
    Returns { run_id, chain_ok, errors, report }.
    """
    run_id = (body.get("run_id") or "").strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id required")
    tenant_id = (body.get("tenant_id") or "default").strip()
    ok, errors, report = verify_run_replay(tenant_id, run_id)
    return {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "chain_ok": ok,
        "errors": errors,
        "report": report,
    }


@router.get("/{run_id}")
def admin_replay_get(
    run_id: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    GET /v1/admin/replay/{run_id}?tenant_id=default — return replay report for run_id.
    """
    tid = (tenant_id or "default").strip()
    ok, errors, report = verify_run_replay(tid, run_id)
    return {
        "run_id": run_id,
        "tenant_id": tid,
        "chain_ok": ok,
        "errors": errors,
        "report": report,
    }
