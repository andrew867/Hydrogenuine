from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from hg_gateway.db import get_connection


def _gateway_db_path(workspace_root: Path) -> str | None:
    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    try:
        return str((workspace_root / "memory" / "gateway.sqlite3").resolve())
    except Exception:
        return None


def record_human_notification(
    workspace_root: Path,
    *,
    task_name: str,
    kind: str = "run_update",
    message: str = "",
    summary: Optional[dict[str, Any]] = None,
    transport: str = "log_only",
    recipient: str = "The Reverend",
    social_account_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    operational_agent_id: Optional[str] = None,
) -> dict[str, Any]:
    """Persist a normalized human-directed notification payload.

    Delivery stays downstream. This helper only records the durable operator-facing
    receipt that scripts and DAG tools can share.
    """
    recorded_at = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    ts = recorded_at.split(".")[0] + "Z"
    out_dir = workspace_root / "memory" / "automation" / "notifications"
    out_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": ts,
        "task_name": str(task_name or "").strip() or "unknown",
        "channel": "human",
        "recipient": recipient,
        "kind": str(kind or "run_update").strip() or "run_update",
        "transport": str(transport or "log_only").strip() or "log_only",
        "message": str(message or "").strip(),
        "summary": summary if isinstance(summary, dict) else {},
    }
    if social_account_id:
        entry["social_account_id"] = str(social_account_id).strip()
    if tenant_id:
        entry["tenant_id"] = str(tenant_id).strip()
    if operational_agent_id:
        entry["operational_agent_id"] = str(operational_agent_id).strip()
    db_path = _gateway_db_path(workspace_root)
    if db_path:
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO human_notifications (
                        notification_id, recorded_at, timestamp, task_name, channel, recipient, kind, transport,
                        message, summary_json, social_account_id, tenant_id, operational_agent_id, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        recorded_at,
                        entry["timestamp"],
                        entry["task_name"],
                        entry["channel"],
                        entry["recipient"],
                        entry["kind"],
                        entry["transport"],
                        entry["message"],
                        json.dumps(entry["summary"], ensure_ascii=False),
                        entry.get("social_account_id"),
                        entry.get("tenant_id"),
                        entry.get("operational_agent_id"),
                        json.dumps(entry, ensure_ascii=False),
                    ),
                )
        except Exception:
            pass
    primary_path = out_dir / "human_notifications.jsonl"
    legacy_path = out_dir / "telegram_notifications.jsonl"
    for candidate in (primary_path, legacy_path):
        try:
            with candidate.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return {
        "entry": entry,
        "notification_log": str(primary_path),
    }


def list_human_notifications(workspace_root: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    db_path = _gateway_db_path(workspace_root)
    if db_path:
        try:
            with get_connection(db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT payload_json, recorded_at, timestamp, notification_id
                    FROM human_notifications
                    ORDER BY recorded_at DESC, timestamp DESC, notification_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            items: list[dict[str, Any]] = []
            for row in rows:
                payload_raw = row[0] if not isinstance(row, dict) else row.get("payload_json")
                try:
                    payload = json.loads(payload_raw) if payload_raw else {}
                except (TypeError, json.JSONDecodeError):
                    payload = {}
                if isinstance(payload, dict):
                    items.append(payload)
            if items:
                return items
        except Exception:
            pass
    return []
