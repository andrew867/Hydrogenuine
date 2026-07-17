from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection
from hg_gateway.task_registry import (
    get_task_registry_entry,
    get_task_registry_summary,
    list_task_inventory,
    list_task_versions,
    sync_task_registry,
)


def get_task_registry_overview() -> dict[str, Any]:
    with get_connection() as conn:
        summary = get_task_registry_summary(conn)
        tasks = list_task_inventory(conn)
    return {"summary": summary, "tasks": tasks}


def get_task_registry_record(task_name: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        return get_task_registry_entry(conn, task_name)


def get_task_registry_record_versions(task_name: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_task_versions(conn, task_name)


def sync_task_registry_service(root: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        return sync_task_registry(conn, root=None if root is None else Path(root))


def save_task_registry_record(
    task_name: str,
    *,
    metadata: dict[str, Any] | None = None,
    disabled: bool | None = None,
    archived: bool | None = None,
    source_path: str | None = None,
    mode: str | None = None,
    model: str | None = None,
    sandbox_mode: str | None = None,
    sandbox_allowlist: list[str] | None = None,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        record = get_task_registry_entry(conn, task_name)
        if record is None:
            return None
        payload = json.loads(record.get("payload_json") or "{}") if record.get("payload_json") else {}
        if metadata:
            payload.update(metadata)
        if source_path is not None:
            record["source_path"] = source_path
            payload["source_path"] = source_path
        if mode is not None:
            record["mode"] = mode
            payload["mode"] = mode
        if model is not None:
            record["model"] = model
            payload["model"] = model
        if sandbox_mode is not None:
            record["sandbox_mode"] = sandbox_mode
            payload["sandbox_mode"] = sandbox_mode
        if sandbox_allowlist is not None:
            record["sandbox_allowlist"] = sandbox_allowlist
            payload["sandbox_allowlist"] = sandbox_allowlist
        if disabled is not None:
            record["active"] = 0 if disabled else 1
            payload["disabled"] = bool(disabled)
        if archived is not None:
            record["latest_status"] = "archived" if archived else "current"
            payload["archived"] = bool(archived)
        latest_status = "current"
        if payload.get("archived"):
            latest_status = "archived"
        elif payload.get("disabled"):
            latest_status = "disabled"
        record["active"] = 0 if latest_status in {"archived", "disabled"} else 1
        record["latest_status"] = latest_status

        version_row = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) AS n FROM task_registry_versions WHERE task_name = ?",
            (task_name,),
        ).fetchone()
        next_version = int(version_row["n"] if version_row else 0) + 1
        version_id = f"{task_name}:v{next_version}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        conn.execute(
            """
            INSERT INTO task_registry_versions (
                version_id, task_name, version_number, state,
                job_id, session_target, platform_id, mode, model,
                source_path, source_sha256, source_size_bytes, source_mtime,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                task_name,
                next_version,
                "edited",
                record["job_id"],
                record["session_target"],
                record.get("platform_id"),
                record["mode"],
                record.get("model"),
                record["source_path"],
                record["source_sha256"],
                record["source_size_bytes"],
                record.get("source_mtime"),
                None,
                "task registry edit",
                now,
                now,
                json.dumps({**payload, "version_id": version_id, "version_number": next_version}, sort_keys=True),
            ),
        )
        conn.execute(
            """
            UPDATE task_registry_entries
            SET source_path = ?, mode = ?, model = ?, active = ?, latest_status = ?, current_version_id = ?, updated_at = ?, payload_json = ?
            WHERE task_name = ?
            """,
            (
                record["source_path"],
                record["mode"],
                record.get("model"),
                int(record.get("active", 1)),
                latest_status,
                version_id,
                now,
                json.dumps({**payload, "current_version_id": version_id, "latest_status": latest_status}, sort_keys=True),
                task_name,
            ),
        )
        return get_task_registry_entry(conn, task_name)
