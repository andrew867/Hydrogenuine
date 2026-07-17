"""
Schedule API: POST/GET/PATCH /v1/schedule/jobs, POST /v1/schedule/jobs/{id}/run_once.
Tenant-scoped and audited. run_once creates a pending schedule_run_request for scheduler to consume.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.db import get_connection
from hg_gateway.store import get_store
from hg_core.gate import enforce_release_gate
from hg_core.tenancy.context import TenantContext

router = APIRouter(prefix="/schedule", tags=["schedule"], dependencies=[Depends(verify_api_key)])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit(tenant_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    store = get_store()
    if hasattr(store, "audit_append"):
        store.audit_append(tenant_id, event_type, payload)


@router.post("/jobs")
def create_scheduled_job(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Create a scheduled job. Requires job_id and exactly one of cron or interval_minutes."""
    job_id = (body.get("job_id") or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    cron = body.get("cron")
    interval_minutes = body.get("interval_minutes")
    if cron is None and interval_minutes is None:
        raise HTTPException(status_code=400, detail="Exactly one of cron or interval_minutes is required")
    if cron is not None and interval_minutes is not None:
        raise HTTPException(status_code=400, detail="Provide only one of cron or interval_minutes")
    if cron is not None:
        cron = str(cron).strip()
        interval_minutes = None
    else:
        try:
            interval_minutes = float(interval_minutes)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="interval_minutes must be a number")
    inputs = body.get("inputs")
    if inputs is None:
        inputs = {}
    inputs_json = json.dumps(inputs) if isinstance(inputs, dict) else "{}"
    tenant_id = tenant_context.tenant_id
    now = _now()
    with get_connection() as conn:
        try:
            conn.execute(
                """INSERT INTO scheduled_jobs (tenant_id, job_id, cron, interval_minutes, inputs_json, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
                (tenant_id, job_id, cron, interval_minutes, inputs_json, now, now),
            )
        except Exception as e:
            if "UNIQUE" in str(e) or "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail=f"Job {job_id} already exists for this tenant")
            raise
    _audit(tenant_id, "schedule.created", {"job_id": job_id, "cron": cron, "interval_minutes": interval_minutes})
    return {"ok": True, "tenant_id": tenant_id, "job_id": job_id, "cron": cron, "interval_minutes": interval_minutes}


@router.get("/jobs")
def list_scheduled_jobs(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """List scheduled jobs for the current tenant."""
    tenant_id = tenant_context.tenant_id
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT job_id, cron, interval_minutes, inputs_json, status, created_at, updated_at FROM scheduled_jobs WHERE tenant_id = ? ORDER BY job_id",
            (tenant_id,),
        ).fetchall()
    jobs = []
    for r in rows:
        jobs.append({
            "job_id": r["job_id"],
            "cron": r["cron"],
            "interval_minutes": r["interval_minutes"],
            "inputs": json.loads(r["inputs_json"]) if r["inputs_json"] else {},
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    return {"jobs": jobs}


@router.patch("/jobs/{job_id}")
def update_scheduled_job(
    job_id: str,
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Update a scheduled job. Only provided fields are updated."""
    tenant_id = tenant_context.tenant_id
    with get_connection() as conn:
        row = conn.execute(
            "SELECT job_id, cron, interval_minutes, inputs_json, status FROM scheduled_jobs WHERE tenant_id = ? AND job_id = ?",
            (tenant_id, job_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        updates = []
        params = []
        if "cron" in body:
            updates.append("cron = ?")
            params.append(body["cron"] if body["cron"] is not None else None)
        if "interval_minutes" in body:
            updates.append("interval_minutes = ?")
            params.append(body["interval_minutes"])
        if "inputs" in body:
            updates.append("inputs_json = ?")
            params.append(json.dumps(body["inputs"]) if isinstance(body["inputs"], dict) else "{}")
        if "status" in body:
            updates.append("status = ?")
            params.append(str(body["status"]).strip() or "active")
        if not updates:
            return {"ok": True, "job_id": job_id}
        updates.append("updated_at = ?")
        params.append(_now())
        params.append(tenant_id)
        params.append(job_id)
        conn.execute(
            f"UPDATE scheduled_jobs SET {', '.join(updates)} WHERE tenant_id = ? AND job_id = ?",
            params,
        )
    _audit(tenant_id, "schedule.updated", {"job_id": job_id, "body_keys": list(body.keys())})
    return {"ok": True, "job_id": job_id}


@router.post("/jobs/{job_id}/run_once")
def run_once(
    job_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Request a one-off run of the job. Creates a pending run request for the scheduler to consume."""
    tenant_id = tenant_context.tenant_id
    with get_connection() as conn:
        row = conn.execute(
            "SELECT job_id FROM scheduled_jobs WHERE tenant_id = ? AND job_id = ? AND status = 'active'",
            (tenant_id, job_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found or not active")
        if (os.environ.get("HG_RELEASE_GATE_ENFORCED") or "0").strip().lower() not in {"0", "false", "no", "off"}:
            gate = enforce_release_gate(workflow_family=job_id, target_kind="workflow", target_id=job_id)
            if not gate.get("ok"):
                raise HTTPException(status_code=423, detail={"code": gate.get("code"), "message": gate.get("reason")})
        existing = conn.execute(
            """
            SELECT id
            FROM schedule_run_requests
            WHERE tenant_id = ? AND job_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
            """,
            (tenant_id, job_id),
        ).fetchone()
        if existing:
            return {"ok": True, "request_id": str(existing["id"]), "job_id": job_id, "status": "pending", "deduped": True}
        request_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            """INSERT INTO schedule_run_requests (id, tenant_id, job_id, requested_at, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (request_id, tenant_id, job_id, now, now),
        )
    _audit(tenant_id, "schedule.run_once", {"job_id": job_id, "request_id": request_id})
    return {"ok": True, "request_id": request_id, "job_id": job_id, "status": "pending"}


@router.get("/run_requests")
def list_run_requests(
    status: Optional[str] = None,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """List run requests for the current tenant (for UI). Scheduler can poll with status=pending for dispatch."""
    tenant_id = tenant_context.tenant_id
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                """SELECT id, job_id, requested_at, status, created_at FROM schedule_run_requests
                   WHERE tenant_id = ? AND status = ? ORDER BY created_at DESC LIMIT 500""",
                (tenant_id, status.strip()),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, job_id, requested_at, status, created_at FROM schedule_run_requests
                   WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 500""",
                (tenant_id,),
            ).fetchall()
    requests = [
        {"id": r["id"], "job_id": r["job_id"], "requested_at": r["requested_at"], "status": r["status"], "created_at": r["created_at"]}
        for r in rows
    ]
    return {"run_requests": requests}
