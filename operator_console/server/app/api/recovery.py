"""Recovery hub API: summary and operator action recording."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.recovery_actions_service import build_recovery_summary, record_recovery_action

router = APIRouter()


@router.get("/summary")
def recovery_summary(stale_minutes: int = 30, _=Depends(require_api_key)) -> Dict[str, Any]:
    return build_recovery_summary(stale_minutes=stale_minutes)


class RecoveryActionBody(BaseModel):
    action: str = Field(..., description="cancel_run | retry_run | reset_breaker | purge_run | retention_cleanup")
    target_type: str
    target_id: str
    actor_id: str = "operator"
    details: Optional[Dict[str, Any]] = None


@router.post("/actions")
def recovery_action(body: RecoveryActionBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    allowed = {
        "cancel_run",
        "cancel_stale_runs",
        "retry_run",
        "replay_run",
        "reset_breaker",
        "purge_run",
        "retention_cleanup",
        "resume_run",
    }
    if body.action not in allowed:
        raise HTTPException(status_code=400, detail=f"unknown action: {body.action}")

    result_details: Dict[str, Any] = dict(body.details or {})
    try:
        if body.action == "cancel_run":
            from ..services.replay_ops import cancel_run
            result_details["api_result"] = cancel_run(body.target_id)
        elif body.action == "cancel_stale_runs":
            from ..services.replay_ops import cancel_stale_runs
            minutes = int((body.details or {}).get("stale_minutes") or 30)
            result_details["api_result"] = cancel_stale_runs(stale_minutes=minutes)
        elif body.action == "replay_run":
            from ..services.replay_ops import replay_run
            result_details["api_result"] = replay_run(body.target_id)
        elif body.action == "resume_run":
            from ..services.run_ops import resume_run
            result_details["api_result"] = resume_run(body.target_id)
        elif body.action == "reset_breaker":
            from hg_core.task_graph.circuit_breaker import reset_breaker as cb_reset
            from hg_lib.config import get_workspace_root
            workflow_id = body.target_id
            destination = (body.details or {}).get("destination")
            cb_reset(get_workspace_root(), workflow_id, destination)
            result_details["breaker_key"] = f"{workflow_id}:{destination}" if destination else workflow_id
        elif body.action == "purge_run":
            from hg_core.task_graph.retention_redaction_purge import purge_by_run_id
            from hg_lib.config import get_workspace_root
            removed, audit_entry = purge_by_run_id(get_workspace_root(), body.target_id)
            result_details["removed_count"] = len(removed)
            result_details["audit_entry"] = audit_entry
        elif body.action == "retention_cleanup":
            from hg_core.retention.worker import run_retention_job
            from hg_lib.config import get_workspace_root
            days = int((body.details or {}).get("retention_days") or 365)
            dry_run = bool((body.details or {}).get("dry_run"))
            result_details["api_result"] = run_retention_job(
                scope={"type": "workspace", "id": "operator"},
                actor={"agent_id": body.actor_id, "pubkey": "0", "key_id": "operator"},
                workspace_root=get_workspace_root(),
                retention_days=days,
                dry_run=dry_run,
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    recorded = record_recovery_action(
        action=body.action,
        target_type=body.target_type,
        target_id=body.target_id,
        actor_id=body.actor_id,
        details=result_details,
    )
    return {**recorded, "action_result": result_details}
