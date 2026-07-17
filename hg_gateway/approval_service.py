"""
Approval service with gateway persistence (Social Media Entity Tools).
Create request, approve, reject, request_edit; all read/write to approval_requests table.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection, _get_db_path


STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_REQUEST_EDIT = "request_edit"


def _get_conn(db_path: Optional[str] = None):
    return get_connection(db_path or _get_db_path())


def _merge_preview_resolution_context(
    conn,
    *,
    approval_id: str,
    tenant_id: str,
    decision: str,
    decision_note: str,
    decided_by: str,
    resolution_context: Optional[Dict[str, Any]],
) -> None:
    if not isinstance(resolution_context, dict):
        resolution_context = {}
    row = conn.execute(
        "SELECT preview_json FROM approval_requests WHERE approval_id = ? AND tenant_id = ?",
        (approval_id, tenant_id),
    ).fetchone()
    if not row:
        return
    preview_raw = row[0]
    if isinstance(preview_raw, str):
        try:
            preview = json.loads(preview_raw) if preview_raw else {}
        except Exception:
            preview = {}
    elif isinstance(preview_raw, dict):
        preview = dict(preview_raw)
    else:
        preview = {}
    if not isinstance(preview, dict):
        preview = {}
    existing_context = preview.get("resolution_context") if isinstance(preview.get("resolution_context"), dict) else {}
    merged_context = {
        "decision": decision,
        "note": decision_note or "",
        "decided_by": decided_by or "",
        "rationale": str(resolution_context.get("rationale") or existing_context.get("rationale") or "").strip(),
        "release_scope": str(resolution_context.get("release_scope") or existing_context.get("release_scope") or "").strip(),
        "followup_expectation": str(resolution_context.get("followup_expectation") or existing_context.get("followup_expectation") or "").strip(),
        "followup_window_hours": _coerce_followup_window_hours(
            resolution_context.get("followup_window_hours"),
            existing_context.get("followup_window_hours"),
        ),
    }
    preview["resolution_context"] = merged_context
    conn.execute(
        "UPDATE approval_requests SET preview_json = ? WHERE approval_id = ? AND tenant_id = ?",
        (json.dumps(preview), approval_id, tenant_id),
    )


def _coerce_followup_window_hours(*values: Any) -> int | None:
    for raw in values:
        if raw in {None, ""}:
            continue
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            continue
    return None


class ApprovalService:
    """Create and resolve approval requests; persistence in gateway approval_requests table."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or _get_db_path()

    def create_request(
        self,
        entity_id: str,
        action_kind: str,
        preview_json: Dict[str, Any],
        tenant_id: str = "default",
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        target_platform: Optional[str] = None,
        target_account_alias: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new approval request (status pending). Returns the created row as dict."""
        approval_id = str(uuid.uuid4())
        with _get_conn(self._db_path) as conn:
            conn.execute(
                """INSERT INTO approval_requests (
                    approval_id, tenant_id, entity_id, workflow_id, step_id, action_kind,
                    target_platform, target_account_alias, preview_json, status,
                    requested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    approval_id,
                    tenant_id,
                    entity_id,
                    workflow_id,
                    step_id,
                    action_kind,
                    target_platform,
                    target_account_alias,
                    __import__("json").dumps(preview_json),
                    STATUS_PENDING,
                ),
            )
        return self.get_request(approval_id, tenant_id) or {}

    def get_request(self, approval_id: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """Fetch approval request by id and tenant."""
        with _get_conn(self._db_path) as conn:
            row = conn.execute(
                """SELECT approval_id, tenant_id, entity_id, workflow_id, step_id, action_kind,
                          target_platform, target_account_alias, preview_json, status,
                          requested_at, decided_at, decided_by, decision_note
                   FROM approval_requests WHERE approval_id = ? AND tenant_id = ?""",
                (approval_id, tenant_id),
            ).fetchone()
            if not row:
                return None
            return _row_to_approval_request(row)

    def list_pending(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """List pending approval requests for tenant."""
        with _get_conn(self._db_path) as conn:
            rows = conn.execute(
                """SELECT approval_id, tenant_id, entity_id, workflow_id, step_id, action_kind,
                          target_platform, target_account_alias, preview_json, status,
                          requested_at, decided_at, decided_by, decision_note
                   FROM approval_requests WHERE tenant_id = ? AND status = ? ORDER BY requested_at""",
                (tenant_id, STATUS_PENDING),
            ).fetchall()
            return [_row_to_approval_request(r) for r in rows]

    def approve(
        self,
        approval_id: str,
        tenant_id: str = "default",
        decided_by: str = "",
        decision_note: Optional[str] = None,
        resolution_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark request approved; set decided_at, decided_by, decision_note."""
        with _get_conn(self._db_path) as conn:
            conn.execute(
                """UPDATE approval_requests SET status = ?, decided_at = datetime('now'), decided_by = ?, decision_note = ?
                   WHERE approval_id = ? AND tenant_id = ? AND status = ?""",
                (STATUS_APPROVED, decided_by or "", decision_note or "", approval_id, tenant_id, STATUS_PENDING),
            )
            _merge_preview_resolution_context(
                conn,
                approval_id=approval_id,
                tenant_id=tenant_id,
                decision=STATUS_APPROVED,
                decision_note=decision_note or "",
                decided_by=decided_by or "",
                resolution_context=resolution_context,
            )
        return self.get_request(approval_id, tenant_id)

    def reject(
        self,
        approval_id: str,
        tenant_id: str = "default",
        decided_by: str = "",
        decision_note: Optional[str] = None,
        resolution_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark request rejected."""
        with _get_conn(self._db_path) as conn:
            conn.execute(
                """UPDATE approval_requests SET status = ?, decided_at = datetime('now'), decided_by = ?, decision_note = ?
                   WHERE approval_id = ? AND tenant_id = ? AND status = ?""",
                (STATUS_REJECTED, decided_by or "", decision_note or "", approval_id, tenant_id, STATUS_PENDING),
            )
            _merge_preview_resolution_context(
                conn,
                approval_id=approval_id,
                tenant_id=tenant_id,
                decision=STATUS_REJECTED,
                decision_note=decision_note or "",
                decided_by=decided_by or "",
                resolution_context=resolution_context,
            )
        return self.get_request(approval_id, tenant_id)

    def request_edit(
        self,
        approval_id: str,
        tenant_id: str = "default",
        decided_by: str = "",
        decision_note: Optional[str] = None,
        resolution_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark request as request_edit (operator asked for changes)."""
        with _get_conn(self._db_path) as conn:
            conn.execute(
                """UPDATE approval_requests SET status = ?, decided_at = datetime('now'), decided_by = ?, decision_note = ?
                   WHERE approval_id = ? AND tenant_id = ? AND status = ?""",
                (STATUS_REQUEST_EDIT, decided_by or "", decision_note or "", approval_id, tenant_id, STATUS_PENDING),
            )
            _merge_preview_resolution_context(
                conn,
                approval_id=approval_id,
                tenant_id=tenant_id,
                decision=STATUS_REQUEST_EDIT,
                decision_note=decision_note or "",
                decided_by=decided_by or "",
                resolution_context=resolution_context,
            )
        return self.get_request(approval_id, tenant_id)


def _row_to_approval_request(row: Any) -> Dict[str, Any]:
    preview = row[8]
    if isinstance(preview, str):
        try:
            preview = json.loads(preview) if preview else {}
        except Exception:
            preview = {}
    return {
        "approval_id": row[0],
        "tenant_id": row[1],
        "entity_id": row[2],
        "workflow_id": row[3],
        "step_id": row[4],
        "action_kind": row[5],
        "target_platform": row[6],
        "target_account_alias": row[7],
        "preview_json": preview,
        "status": row[9],
        "requested_at": row[10],
        "decided_at": row[11],
        "decided_by": row[12],
        "decision_note": row[13],
    }
