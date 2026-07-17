"""Operator API: status overview, run detail, incident queue, approvals, and actions."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hg_gateway.approval_summary import normalize_runtime_approval

from ..core.auth import require_api_key

router = APIRouter()


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _runtime_tenant_id() -> str:
    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _ux():
    from hg_core.task_graph import operator_ux
    return operator_ux


def _enrich_runtime_approval(row: dict) -> dict:
    if not isinstance(row, dict):
        return row
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    entity_approval_id = str(payload.get("entity_approval_id") or "").strip()
    if not entity_approval_id:
        return row
    try:
        from .approvals_entity import _service as entity_approval_service, _enrich_review_release_state
        from ..services.review_handoff_summary import build_workflow_status_summary
    except Exception:
        return row
    try:
        entity_row = entity_approval_service().get_request(entity_approval_id, tenant_id=_runtime_tenant_id())
    except Exception:
        entity_row = None
    if not isinstance(entity_row, dict):
        return row
    enriched = _enrich_review_release_state(entity_row)
    row["entity_approval_id"] = entity_approval_id
    row["review_release_state"] = enriched.get("review_release_state") if isinstance(enriched, dict) else None
    workflow_id = str(payload.get("workflow_id") or payload.get("graph_id") or row.get("workflow_id") or row.get("workflow") or "").strip()
    if workflow_id:
        try:
            root = _workspace_root()
            row["workflow_status_summary"] = build_workflow_status_summary(
                root,
                workflow_id=workflow_id,
                job_id=str(payload.get("job_id") or "").strip() or None,
                graph_id=str(payload.get("graph_id") or "").strip() or None,
            )
        except Exception:
            row["workflow_status_summary"] = None
    return row


@router.get("/explain-block")
def explain_block_endpoint(
    work_item_id: str | None = None,
    action_id: str | None = None,
    _=Depends(require_api_key),
):
    """Explain why a work item or action is blocked (control-surface materialized index)."""
    if not work_item_id and not action_id:
        raise HTTPException(status_code=400, detail="work_item_id or action_id required")
    try:
        from hg_core.control_surface import explain_block

        root = _workspace_root()
        if root is None:
            raise HTTPException(status_code=503, detail="workspace root unavailable")
        result = explain_block(root, work_item_id=work_item_id, action_id=action_id)
        if result is None:
            raise HTTPException(status_code=400, detail="work_item_id or action_id required")
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/status-overview")
def status_overview(_=Depends(require_api_key)):
    """Status overview: recent, paused, failing, expensive, breaker_states."""
    try:
        root = _workspace_root()
        data = _ux().get_status_overview(root)
        return {"ok": True, **data}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/run-detail/{run_id}")
def run_detail(run_id: str, _=Depends(require_api_key)):
    """Run detail: summary, trace link, failure class, retries."""
    try:
        root = _workspace_root()
        data = _ux().get_run_detail(run_id, root)
        return {"ok": True, **data}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/incident-queue")
def incident_queue(_=Depends(require_api_key)):
    """Incident queue: list of terminal failures."""
    try:
        root = _workspace_root()
        items = _ux().get_dead_letter_queue(root)
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/approvals")
def approvals_queue(
    workflow_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _=Depends(require_api_key),
):
    """Runtime approvals queue with optional workflow and status filter (pending, approved, denied, all)."""
    try:
        from hg_gateway.store import get_store
        from ..services.activity_service import get_recent_activity

        status_filter = (status or "pending").strip().lower()
        if status_filter not in ("pending", "all", "approved", "denied"):
            status_filter = "pending"
        approvals = [
            _enrich_runtime_approval(normalize_runtime_approval(item))
            for item in get_store().approval_list(_runtime_tenant_id(), status_filter=status_filter)
        ]
        if workflow_id:
            approvals = [item for item in approvals if item.get("workflow_id") == workflow_id or item.get("workflow") == workflow_id]
        approvals.sort(key=lambda row: str(row.get("createdAt") or row.get("timestamp") or ""), reverse=True)
        total = len(approvals)
        activity = get_recent_activity(limit_runs=8, limit_decisions=12)
        return {
            "ok": True,
            "items": approvals[offset : offset + limit],
            "total": total,
            "evidence_timeline": activity.get("evidence_timeline"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class ReplayBody(BaseModel):
    incident_id: str
    shadow: bool = True


@router.post("/replay-incident")
def replay_incident(body: ReplayBody, _=Depends(require_api_key)):
    """Replay an incident entry in shadow (no side effects)."""
    try:
        root = _workspace_root()
        result = _ux().replay_dead_letter(body.incident_id, shadow=body.shadow, workspace_root=root)
        return {"ok": result.get("ok", False), **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class WorkflowBody(BaseModel):
    workflow_id: str


@router.post("/pause")
def pause_workflow(body: WorkflowBody, _=Depends(require_api_key)):
    """Pause a workflow."""
    try:
        root = _workspace_root()
        result = _ux().pause_workflow(body.workflow_id, root)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/resume")
def resume_workflow(body: WorkflowBody, _=Depends(require_api_key)):
    """Resume a paused workflow."""
    try:
        root = _workspace_root()
        result = _ux().resume_workflow(body.workflow_id, root)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/rollback")
def rollback_workflow(body: WorkflowBody, _=Depends(require_api_key)):
    """Rollback workflow to last known good."""
    try:
        root = _workspace_root()
        result = _ux().rollback_to_last_good(body.workflow_id, root)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/export-weekly-report")
def export_weekly_report(_=Depends(require_api_key)):
    """Export weekly report."""
    try:
        root = _workspace_root()
        result = _ux().export_weekly_report(root)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class EvaluateApprovalBody(BaseModel):
    workflow_id: str
    action_summary: dict = {}


@router.post("/approval/evaluate")
def evaluate_approval(body: EvaluateApprovalBody, _=Depends(require_api_key)):
    """Evaluate approval (default-approve, strict blacklist)."""
    try:
        root = _workspace_root()
        result = _ux().evaluate_approval(body.workflow_id, body.action_summary, root)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
