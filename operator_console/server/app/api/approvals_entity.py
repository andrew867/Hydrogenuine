"""
Entity approval API routes (Social Media Entity Tools).
POST create request, GET pending, POST /{id}/approve, POST /{id}/reject, POST /{id}/request-edit.
Mounted under /api/v1/approvals-entity.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from hg_core.human_notifications import record_human_notification
from hg_gateway.events_ledger import append_evidence, sha256_json
from hg_gateway.approval_service import ApprovalService

router = APIRouter(tags=["approvals-entity"])


def _tenant_id(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str:
    return (x_tenant_id or "").strip() or "default"


# ---- Request/response models ----


class CreateApprovalRequestBody(BaseModel):
    entity_id: str
    action_kind: str
    preview_json: Dict[str, Any]
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    target_platform: Optional[str] = None
    target_account_alias: Optional[str] = None


class ApproveRejectBody(BaseModel):
    note: Optional[str] = None
    decided_by: Optional[str] = None
    rationale: Optional[str] = None
    release_scope: Optional[str] = None
    followup_expectation: Optional[str] = None
    followup_window_hours: Optional[int] = None
    refresh_reason_codes: Optional[list[str]] = None


# ---- Service singleton (uses gateway DB path from env) ----


def _service() -> ApprovalService:
    return ApprovalService()


def _workspace_root():
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _enrich_review_release_state(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return row
    task_name = str(row.get("workflow_id") or row.get("entity_id") or "").strip()
    approval_id = str(row.get("approval_id") or "").strip()
    if not task_name or not approval_id:
        return row
    try:
        from ..services.entities_service import get_entity
    except Exception:
        return row
    try:
        entity = get_entity(task_name)
    except Exception:
        entity = None
    if not isinstance(entity, dict):
        return row
    summary = entity.get("review_handoff_summary") if isinstance(entity.get("review_handoff_summary"), dict) else {}
    latest = summary.get("latest") if isinstance(summary.get("latest"), dict) else {}
    items = summary.get("items") if isinstance(summary.get("items"), list) else []
    matched = next(
        (item for item in items if isinstance(item, dict) and str(item.get("approval_id") or "").strip() == approval_id),
        latest if str(latest.get("approval_id") or "").strip() == approval_id else None,
    )
    release_source = matched if isinstance(matched, dict) else summary
    release_blockers = list(release_source.get("release_blockers") or [])
    post_rebuild = entity.get("post_rebuild_continuity_check") if isinstance(entity.get("post_rebuild_continuity_check"), dict) else {}
    continuity_recovery = entity.get("continuity_recovery_readiness") if isinstance(entity.get("continuity_recovery_readiness"), dict) else {}
    required_next_action = None
    action_hint = None
    if release_blockers:
        if post_rebuild.get("verification_required") and not post_rebuild.get("verified"):
            required_next_action = "verify_rebuild"
            action_hint = "Verify post-rebuild continuity before release."
        elif "continuity_recovery_ack_required" in release_blockers and continuity_recovery.get("can_acknowledge"):
            required_next_action = "acknowledge_recovery"
            action_hint = "Acknowledge bounded continuity recovery before release."
        elif "operational_resume_checkpoint_required" in release_blockers:
            required_next_action = "approve_resume"
            action_hint = "Approve a fresh operational resume checkpoint before release."
        elif release_source.get("refresh_recommended"):
            required_next_action = "refresh_handoff"
            action_hint = "Refresh this handoff because the approval context is stale."
    row["review_release_state"] = {
        "release_ready": bool(release_source.get("release_ready")),
        "release_blockers": release_blockers,
        "release_next_eligible_at": release_source.get("release_next_eligible_at"),
        "refresh_recommended": bool(release_source.get("refresh_recommended")),
        "refresh_reasons": list(release_source.get("refresh_reasons") or []),
        "latest_release_attempt": release_source.get("latest_release_attempt") if isinstance(release_source.get("latest_release_attempt"), dict) else None,
        "followup_summary": release_source.get("followup_summary") if isinstance(release_source.get("followup_summary"), dict) else None,
        "continuity_recovery_readiness": continuity_recovery,
        "post_rebuild_continuity_check": post_rebuild,
        "operational_resume_governance_summary": entity.get("operational_resume_governance_summary") if isinstance(entity.get("operational_resume_governance_summary"), dict) else {},
        "operational_resume_checkpoint": entity.get("operational_resume_checkpoint") if isinstance(entity.get("operational_resume_checkpoint"), dict) else {},
        "platform": entity.get("platform") or row.get("target_platform"),
        "operational_agent_id": entity.get("operational_agent_id"),
        "required_next_action": required_next_action,
        "action_hint": action_hint,
    }
    return row


def _record_review_handoff_resolution(row: Dict[str, Any], *, decision: str, note: str, decided_by: str) -> None:
    root = _workspace_root()
    if root is None or not isinstance(row, dict):
        return
    preview = row.get("preview_json") if isinstance(row.get("preview_json"), dict) else {}
    resolution_context = preview.get("resolution_context") if isinstance(preview.get("resolution_context"), dict) else {}
    task_name = str(row.get("workflow_id") or row.get("entity_id") or "").strip() or "unknown"
    approval_id = str(row.get("approval_id") or "").strip()
    release_window_hours = None
    approved_until = None
    try:
        raw_hours = preview.get("release_window_hours")
        if raw_hours not in {None, ""}:
            release_window_hours = max(1, int(raw_hours))
            decided_at = str(row.get("decided_at") or "").strip()
            if decided_at:
                decided_dt = datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
                if decided_dt.tzinfo is None:
                    decided_dt = decided_dt.replace(tzinfo=UTC)
                approved_until = (decided_dt.astimezone(UTC) + timedelta(hours=release_window_hours)).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        release_window_hours = None
        approved_until = None
    record_human_notification(
        root,
        task_name=task_name,
        kind="review_handoff_resolution",
        message=f"{task_name} review handoff {decision}: {approval_id or 'unknown approval'}",
        summary={
            "review_handoff": {
                "approval_id": approval_id,
                "decision": decision,
                "decision_note": note,
                "decided_by": decided_by,
                "resolution_context": resolution_context,
                "release_window_hours": release_window_hours,
                "approved_until": approved_until,
                "entity_id": row.get("entity_id"),
                "workflow_id": row.get("workflow_id"),
                "target_platform": row.get("target_platform"),
                "summary": preview.get("summary"),
            }
        },
        transport="log_only",
        operational_agent_id=str(preview.get("operational_agent_id") or "").strip() or None,
    )
    support_claim = {
        "approval_id": approval_id,
        "task_name": task_name,
        "decision": decision,
        "decision_note": note,
        "decided_by": decided_by,
        "release_window_hours": release_window_hours,
        "approved_until": approved_until,
        "entity_id": row.get("entity_id"),
        "workflow_id": row.get("workflow_id"),
        "target_platform": row.get("target_platform"),
        "resolution_context": resolution_context,
        "preview_summary": preview.get("summary"),
    }
    try:
        with open(root / "memory" / "automation" / "notifications" / "support_claims.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps({**support_claim, "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z")}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    try:
        append_evidence(
            str(row.get("tenant_id") or "default").strip() or "default",
            "support_claim",
            sha256_json(support_claim),
            content_ref=json.dumps(support_claim, ensure_ascii=False, sort_keys=True),
            approval_id=approval_id or None,
        )
    except Exception:
        pass


def _record_review_handoff_refresh(old_row: Dict[str, Any], new_row: Dict[str, Any], *, note: str, decided_by: str) -> None:
    root = _workspace_root()
    if root is None or not isinstance(old_row, dict) or not isinstance(new_row, dict):
        return
    preview = new_row.get("preview_json") if isinstance(new_row.get("preview_json"), dict) else {}
    task_name = str(new_row.get("workflow_id") or new_row.get("entity_id") or "").strip() or "unknown"
    new_approval_id = str(new_row.get("approval_id") or "").strip()
    old_approval_id = str(old_row.get("approval_id") or "").strip()
    record_human_notification(
        root,
        task_name=task_name,
        kind="agency_gate",
        message=f"{task_name} review handoff refreshed: {old_approval_id or 'unknown'} -> {new_approval_id or 'unknown'}",
        summary={
            "execution": {
                "status": "pending_approval",
                "platform": new_row.get("target_platform"),
                "blocked_reason": "review_handoff_refreshed",
            },
            "agency_control": {},
            "review_handoff": {
                "approval_id": new_approval_id,
                "refreshed_from_approval_id": old_approval_id,
                "title": preview.get("summary"),
                "refresh_note": note,
                "refreshed_by": decided_by,
                "refresh_reason_codes": preview.get("refresh_reason_codes"),
            },
        },
        transport="log_only",
        operational_agent_id=str(preview.get("operational_agent_id") or "").strip() or None,
    )


def _default_refresh_note(reason_codes: list[str]) -> str:
    labels = {
        "followup_overdue": "follow-up overdue",
        "approval_expired": "approval expired",
        "approval_release_held": "release blocked by hold",
        "approval_release_lane_policy_blocked": "release blocked by lane policy",
        "approval_release_outbound_budget_exhausted": "release blocked by outbound budget",
    }
    parts = [labels.get(code, code.replace("_", " ")) for code in reason_codes if code]
    if not parts:
        return ""
    return "; ".join(parts)


@router.get("/pending")
def list_pending_approvals(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Dict[str, Any]:
    """List pending entity approval requests for the tenant."""
    tenant = _tenant_id(x_tenant_id)
    items = _service().list_pending(tenant_id=tenant)
    return {"items": items}


@router.post("")
def create_approval_request(
    body: CreateApprovalRequestBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Create a new approval request (status pending)."""
    tenant = _tenant_id(x_tenant_id)
    row = _service().create_request(
        entity_id=body.entity_id,
        action_kind=body.action_kind,
        preview_json=body.preview_json,
        tenant_id=tenant,
        workflow_id=body.workflow_id,
        step_id=body.step_id,
        target_platform=body.target_platform,
        target_account_alias=body.target_account_alias,
    )
    return row


@router.get("/{approval_id}")
def get_approval_request(
    approval_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Get a single approval request by id."""
    tenant = _tenant_id(x_tenant_id)
    row = _service().get_request(approval_id, tenant_id=tenant)
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return _enrich_review_release_state(row)


@router.post("/{approval_id}/approve")
def approve_request(
    approval_id: str,
    body: Optional[ApproveRejectBody] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Approve an entity approval request."""
    tenant = _tenant_id(x_tenant_id)
    note = (body.note if body else None) or ""
    decided_by = (body.decided_by if body else None) or ""
    resolution_context = {
        "rationale": (body.rationale if body else None) or "",
        "release_scope": (body.release_scope if body else None) or "",
        "followup_expectation": (body.followup_expectation if body else None) or "",
        "followup_window_hours": body.followup_window_hours if body and body.followup_window_hours is not None else None,
    }
    row = _service().approve(
        approval_id,
        tenant_id=tenant,
        decided_by=decided_by,
        decision_note=note,
        resolution_context=resolution_context,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found or not pending")
    _record_review_handoff_resolution(row, decision="approved", note=note, decided_by=decided_by)
    return row


@router.post("/{approval_id}/reject")
def reject_request(
    approval_id: str,
    body: Optional[ApproveRejectBody] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Reject an entity approval request."""
    tenant = _tenant_id(x_tenant_id)
    note = (body.note if body else None) or ""
    decided_by = (body.decided_by if body else None) or ""
    resolution_context = {
        "rationale": (body.rationale if body else None) or "",
        "release_scope": (body.release_scope if body else None) or "",
        "followup_expectation": (body.followup_expectation if body else None) or "",
        "followup_window_hours": body.followup_window_hours if body and body.followup_window_hours is not None else None,
    }
    row = _service().reject(
        approval_id,
        tenant_id=tenant,
        decided_by=decided_by,
        decision_note=note,
        resolution_context=resolution_context,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found or not pending")
    _record_review_handoff_resolution(row, decision="rejected", note=note, decided_by=decided_by)
    return row


@router.post("/{approval_id}/request-edit")
def request_edit_request(
    approval_id: str,
    body: Optional[ApproveRejectBody] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Mark approval request as request_edit (operator asked for changes)."""
    tenant = _tenant_id(x_tenant_id)
    note = (body.note if body else None) or ""
    decided_by = (body.decided_by if body else None) or ""
    resolution_context = {
        "rationale": (body.rationale if body else None) or "",
        "release_scope": (body.release_scope if body else None) or "",
        "followup_expectation": (body.followup_expectation if body else None) or "",
        "followup_window_hours": body.followup_window_hours if body and body.followup_window_hours is not None else None,
    }
    row = _service().request_edit(
        approval_id,
        tenant_id=tenant,
        decided_by=decided_by,
        decision_note=note,
        resolution_context=resolution_context,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found or not pending")
    _record_review_handoff_resolution(row, decision="request_edit", note=note, decided_by=decided_by)
    return row


@router.post("/{approval_id}/refresh")
def refresh_request(
    approval_id: str,
    body: Optional[ApproveRejectBody] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Create a fresh pending approval request from an existing review handoff."""
    tenant = _tenant_id(x_tenant_id)
    note = (body.note if body else None) or ""
    decided_by = (body.decided_by if body else None) or ""
    refresh_reason_codes = [str(code).strip() for code in ((body.refresh_reason_codes if body else None) or []) if str(code).strip()]
    if not note and refresh_reason_codes:
        note = _default_refresh_note(refresh_reason_codes)
    row = _service().get_request(approval_id, tenant_id=tenant)
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")
    preview = row.get("preview_json") if isinstance(row.get("preview_json"), dict) else {}
    next_preview = dict(preview)
    next_preview["refreshed_from_approval_id"] = approval_id
    if note:
        next_preview["refresh_note"] = note
    if decided_by:
        next_preview["refreshed_by"] = decided_by
    if refresh_reason_codes:
        next_preview["refresh_reason_codes"] = refresh_reason_codes
    next_preview["refresh_context"] = {
        "from_approval_id": approval_id,
        "note": note or "",
        "refreshed_by": decided_by or "",
        "source_status": str(row.get("status") or "").strip(),
        "reason_codes": refresh_reason_codes,
    }
    next_row = _service().create_request(
        entity_id=str(row.get("entity_id") or "").strip(),
        action_kind=str(row.get("action_kind") or "").strip(),
        preview_json=next_preview,
        tenant_id=tenant,
        workflow_id=str(row.get("workflow_id") or "").strip() or None,
        step_id=str(row.get("step_id") or "").strip() or None,
        target_platform=str(row.get("target_platform") or "").strip() or None,
        target_account_alias=str(row.get("target_account_alias") or "").strip() or None,
    )
    _record_review_handoff_refresh(row, next_row, note=note, decided_by=decided_by)
    next_row["refreshed_from_approval_id"] = approval_id
    return next_row
