from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from hg_core.human_notifications import record_human_notification
from hg_gateway.db import get_connection


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return default
    return parsed


def _gateway_db_path(workspace_root: Path) -> str | None:
    import os

    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    try:
        return str((workspace_root / "memory" / "gateway.sqlite3").resolve())
    except Exception:
        return None


def _tenant_id(raw: Any = None) -> str:
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    import os

    return (os.environ.get("HG_OPERATOR_TENANT_ID") or os.environ.get("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _row_to_commitment(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    payload = _json_loads(row[15] if not isinstance(row, dict) else row.get("payload_json"), {})
    details = _json_loads(row[7] if not isinstance(row, dict) else row.get("details_json"), {})
    entry = {
        "commitment_id": row[0] if not isinstance(row, dict) else row.get("commitment_id"),
        "tenant_id": row[1] if not isinstance(row, dict) else row.get("tenant_id"),
        "task_name": row[2] if not isinstance(row, dict) else row.get("task_name"),
        "operational_agent_id": row[3] if not isinstance(row, dict) else row.get("operational_agent_id"),
        "entity_id": row[4] if not isinstance(row, dict) else row.get("entity_id"),
        "commitment_kind": row[5] if not isinstance(row, dict) else row.get("commitment_kind"),
        "title": row[6] if not isinstance(row, dict) else row.get("title"),
        "details": details if isinstance(details, dict) else {},
        "status": row[8] if not isinstance(row, dict) else row.get("status"),
        "due_at": row[9] if not isinstance(row, dict) else row.get("due_at"),
        "fulfilled_at": row[10] if not isinstance(row, dict) else row.get("fulfilled_at"),
        "expired_at": row[11] if not isinstance(row, dict) else row.get("expired_at"),
        "resolution_note": row[12] if not isinstance(row, dict) else row.get("resolution_note"),
        "created_at": row[13] if not isinstance(row, dict) else row.get("created_at"),
        "updated_at": row[14] if not isinstance(row, dict) else row.get("updated_at"),
        "payload": payload if isinstance(payload, dict) else {},
    }
    return entry


def _record_notification(
    workspace_root: Path,
    *,
    task_name: str,
    kind: str,
    message: str,
    summary: dict[str, Any],
    tenant_id: str,
    operational_agent_id: str | None = None,
    entity_id: str | None = None,
) -> None:
    record_human_notification(
        workspace_root,
        task_name=task_name,
        kind=kind,
        message=message,
        summary=summary,
        transport="db_first",
        recipient="The Reverend",
        social_account_id=None,
        tenant_id=tenant_id,
        operational_agent_id=operational_agent_id,
    )


def record_commitment(
    workspace_root: Path,
    *,
    task_name: str,
    title: str,
    details: dict[str, Any] | None = None,
    due_at: str | None = None,
    commitment_kind: str = "promise",
    status: str = "open",
    tenant_id: str | None = None,
    entity_id: str | None = None,
    operational_agent_id: str | None = None,
    created_by: str | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    tenant = _tenant_id(tenant_id)
    commitment_id = str(uuid.uuid4())
    now = _iso_now()
    payload = {
        "commitment_id": commitment_id,
        "tenant_id": tenant,
        "task_name": str(task_name or "").strip(),
        "title": str(title or "").strip(),
        "details": details if isinstance(details, dict) else {},
        "due_at": due_at,
        "commitment_kind": str(commitment_kind or "promise").strip() or "promise",
        "status": str(status or "open").strip() or "open",
        "entity_id": str(entity_id or "").strip() or None,
        "operational_agent_id": str(operational_agent_id or "").strip() or None,
        "created_by": str(created_by or "").strip() or None,
        "source": str(source or "").strip() or None,
        "source_id": str(source_id or "").strip() or None,
    }
    db_path = _gateway_db_path(workspace_root)
    if not db_path:
        raise RuntimeError("HG_GATEWAY_DB_PATH is required for commitment ledger writes")
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO commitment_records (
                commitment_id, tenant_id, task_name, operational_agent_id, entity_id,
                commitment_kind, title, details_json, status, due_at, fulfilled_at,
                expired_at, resolution_note, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                commitment_id,
                tenant,
                payload["task_name"],
                payload["operational_agent_id"],
                payload["entity_id"],
                payload["commitment_kind"],
                payload["title"],
                _json_dumps(payload["details"]),
                payload["status"],
                due_at,
                None,
                None,
                None,
                now,
                now,
                _json_dumps(payload),
            ),
        )
    _record_notification(
        workspace_root,
        task_name=payload["task_name"],
        kind="commitment_recorded",
        message=f"Commitment recorded: {payload['title']}",
        summary=payload,
        tenant_id=tenant,
        operational_agent_id=payload["operational_agent_id"],
    )
    return payload


def list_commitments(
    workspace_root: Path,
    *,
    tenant_id: str | None = None,
    task_name: str | None = None,
    operational_agent_id: str | None = None,
    entity_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    db_path = _gateway_db_path(workspace_root)
    if not db_path:
        return []
    clauses = ["tenant_id = ?"]
    params: list[Any] = [_tenant_id(tenant_id)]
    if task_name:
        clauses.append("task_name = ?")
        params.append(str(task_name).strip())
    if operational_agent_id:
        clauses.append("operational_agent_id = ?")
        params.append(str(operational_agent_id).strip())
    if entity_id:
        clauses.append("entity_id = ?")
        params.append(str(entity_id).strip())
    if status:
        clauses.append("status = ?")
        params.append(str(status).strip())
    sql = f"""
        SELECT commitment_id, tenant_id, task_name, operational_agent_id, entity_id, commitment_kind,
               title, details_json, status, due_at, fulfilled_at, expired_at, resolution_note,
               created_at, updated_at, payload_json
        FROM commitment_records
        WHERE {' AND '.join(clauses)}
        ORDER BY COALESCE(due_at, created_at) ASC, created_at DESC, commitment_id DESC
        LIMIT ?
    """
    params.append(int(limit))
    with get_connection(db_path) as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_row_to_commitment(row) for row in rows]


def get_commitment(workspace_root: Path, commitment_id: str, *, tenant_id: str | None = None) -> dict[str, Any] | None:
    db_path = _gateway_db_path(workspace_root)
    if not db_path:
        return None
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT commitment_id, tenant_id, task_name, operational_agent_id, entity_id, commitment_kind,
                   title, details_json, status, due_at, fulfilled_at, expired_at, resolution_note,
                   created_at, updated_at, payload_json
            FROM commitment_records
            WHERE commitment_id = ? AND tenant_id = ?
            """,
            (str(commitment_id).strip(), _tenant_id(tenant_id)),
        ).fetchone()
    return _row_to_commitment(row) if row else None


def _set_commitment_status(
    workspace_root: Path,
    *,
    commitment_id: str,
    status: str,
    resolution_note: str | None = None,
    tenant_id: str | None = None,
    kind: str,
    notification_message: str,
) -> dict[str, Any] | None:
    db_path = _gateway_db_path(workspace_root)
    if not db_path:
        return None
    now = _iso_now()
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT commitment_id, tenant_id, task_name, operational_agent_id, entity_id, commitment_kind,
                   title, details_json, status, due_at, fulfilled_at, expired_at, resolution_note,
                   created_at, updated_at, payload_json
            FROM commitment_records
            WHERE commitment_id = ? AND tenant_id = ?
            """,
            (str(commitment_id).strip(), _tenant_id(tenant_id)),
        ).fetchone()
        if row is None:
            return None
        entry = _row_to_commitment(row)
        updates = {
            "fulfilled_at": now if status == "fulfilled" else entry.get("fulfilled_at"),
            "expired_at": now if status == "expired" else entry.get("expired_at"),
            "resolution_note": resolution_note or entry.get("resolution_note"),
        }
        entry.update(updates)
        entry["status"] = status
        entry["updated_at"] = now
        entry["payload"] = {
            **(entry.get("payload") if isinstance(entry.get("payload"), dict) else {}),
            **updates,
            "status": status,
            "updated_at": now,
        }
        conn.execute(
            """
            UPDATE commitment_records
            SET status = ?, fulfilled_at = ?, expired_at = ?, resolution_note = ?, updated_at = ?, payload_json = ?
            WHERE commitment_id = ? AND tenant_id = ?
            """,
            (
                status,
                entry.get("fulfilled_at"),
                entry.get("expired_at"),
                entry.get("resolution_note"),
                now,
                _json_dumps(entry["payload"]),
                str(commitment_id).strip(),
                _tenant_id(tenant_id),
            ),
        )
    _record_notification(
        workspace_root,
        task_name=entry.get("task_name") or "commitment",
        kind=kind,
        message=notification_message,
        summary=entry,
        tenant_id=str(entry.get("tenant_id") or _tenant_id(tenant_id)),
        operational_agent_id=entry.get("operational_agent_id"),
    )
    return entry


def fulfill_commitment(
    workspace_root: Path,
    *,
    commitment_id: str,
    tenant_id: str | None = None,
    resolution_note: str | None = None,
) -> dict[str, Any] | None:
    return _set_commitment_status(
        workspace_root,
        commitment_id=commitment_id,
        status="fulfilled",
        resolution_note=resolution_note,
        tenant_id=tenant_id,
        kind="commitment_fulfilled",
        notification_message=f"Commitment fulfilled: {resolution_note or commitment_id}",
    )


def expire_commitment(
    workspace_root: Path,
    *,
    commitment_id: str,
    tenant_id: str | None = None,
    resolution_note: str | None = None,
) -> dict[str, Any] | None:
    return _set_commitment_status(
        workspace_root,
        commitment_id=commitment_id,
        status="expired",
        resolution_note=resolution_note,
        tenant_id=tenant_id,
        kind="commitment_expired",
        notification_message=f"Commitment expired: {resolution_note or commitment_id}",
    )


def summarize_commitments(commitments: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = [item for item in commitments if isinstance(item, dict)]
    if not items:
        return {
            "status": "none",
            "count": 0,
            "open_count": 0,
            "fulfilled_count": 0,
            "expired_count": 0,
            "overdue_count": 0,
            "recent_commitments": [],
        }
    now = datetime.now(UTC)
    open_items = [item for item in items if str(item.get("status") or "").strip() not in {"fulfilled", "expired"}]
    overdue_items = []
    for item in open_items:
        due_at_raw = str(item.get("due_at") or "").strip()
        if not due_at_raw:
            continue
        try:
            due_at = datetime.fromisoformat(due_at_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if due_at <= now:
            overdue_items.append(item)
    latest = max(items, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""))
    return {
        "status": "overdue" if overdue_items else ("pending" if open_items else "done"),
        "count": len(items),
        "open_count": len(open_items),
        "fulfilled_count": sum(1 for item in items if str(item.get("status") or "").strip() == "fulfilled"),
        "expired_count": sum(1 for item in items if str(item.get("status") or "").strip() == "expired"),
        "overdue_count": len(overdue_items),
        "latest_commitment": latest,
        "recent_commitments": items[:5],
    }
