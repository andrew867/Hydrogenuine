from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from hg_core.job_registry import get_registry


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _infer_source_path(task_name: str, entry: dict[str, Any], root: Path) -> str:
    platform = str(entry.get("platform") or "").strip()
    mode = str(entry.get("mode") or "").strip().replace("-", "_")
    if platform and platform != "dynamic":
        candidate = root / "hg_platforms" / platform / f"{platform}_{mode}.py"
        if candidate.exists():
            return candidate.relative_to(root).as_posix()
    return "hg_core/task_graph/native_task_tools.py"


def _default_sandbox_mode(mode: str | None) -> str:
    raw = str(mode or "").strip().lower()
    if raw in {"auto-post", "engage", "monitor", "maintenance", "publish", "draft", "research"}:
        return "sandbox"
    return "direct"


@dataclass(frozen=True)
class TaskRegistryItem:
    task_name: str
    job_id: str
    session_target: str
    platform_id: str | None
    mode: str
    model: str | None
    source_path: str
    source_sha256: str
    source_size_bytes: int
    source_mtime: str
    metadata_json: str = "{}"


def inventory_task_registry(root: Path | None = None) -> list[TaskRegistryItem]:
    workspace = root or workspace_root()
    registry = get_registry()
    items: list[TaskRegistryItem] = []
    source_text = json.dumps(registry, sort_keys=True, ensure_ascii=False)
    source_hash = _hash_text(source_text)
    source_size = len(source_text.encode("utf-8"))
    source_mtime = _now()
    for task_name, entry in sorted(registry.items(), key=lambda pair: pair[0].lower()):
        sandbox_mode = _default_sandbox_mode(entry.get("mode"))
        payload = {
            "task_name": task_name,
            "job_id": entry.get("job_id"),
            "session_target": entry.get("session_target"),
            "platform_id": entry.get("platform"),
            "mode": entry.get("mode"),
            "model": entry.get("model"),
            "sandbox_mode": sandbox_mode,
            "source_path": _infer_source_path(task_name, entry, workspace),
            "registry_source": "hg_core.job_registry.get_registry",
        }
        items.append(
            TaskRegistryItem(
                task_name=task_name,
                job_id=str(entry.get("job_id") or task_name),
                session_target=str(entry.get("session_target") or ""),
                platform_id=entry.get("platform"),
                mode=str(entry.get("mode") or "unknown"),
                model=entry.get("model"),
                source_path=payload["source_path"],
                source_sha256=source_hash,
                source_size_bytes=source_size,
                source_mtime=source_mtime,
                metadata_json=json.dumps(payload, sort_keys=True),
            )
        )
    return items


def ensure_task_registry_seed(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_registry_entries (
            task_name TEXT PRIMARY KEY,
            job_id TEXT NOT NULL UNIQUE,
            session_target TEXT NOT NULL,
            platform_id TEXT,
            mode TEXT NOT NULL,
            model TEXT,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_size_bytes INTEGER NOT NULL,
            source_mtime TEXT,
            current_version_id TEXT,
            latest_status TEXT NOT NULL DEFAULT 'current',
            active INTEGER NOT NULL DEFAULT 1,
            imported_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_registry_versions (
            version_id TEXT PRIMARY KEY,
            task_name TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'imported',
            job_id TEXT NOT NULL,
            session_target TEXT NOT NULL,
            platform_id TEXT,
            mode TEXT NOT NULL,
            model TEXT,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_size_bytes INTEGER NOT NULL,
            source_mtime TEXT,
            author_id TEXT,
            change_summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            UNIQUE(task_name, version_number)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_entries_platform ON task_registry_entries(platform_id, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_entries_mode ON task_registry_entries(mode, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_entries_session_target ON task_registry_entries(session_target, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_versions_task ON task_registry_versions(task_name, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_versions_created ON task_registry_versions(created_at DESC)")


def _existing_latest_version(conn: Any, task_name: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT version_id, version_number, source_sha256
        FROM task_registry_versions
        WHERE task_name = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (task_name,),
    ).fetchone()
    return dict(row) if row else None


def sync_task_registry(conn: Any, items: Iterable[TaskRegistryItem] | None = None, root: Path | None = None) -> dict[str, Any]:
    inventory = list(items or inventory_task_registry(root))
    ensure_task_registry_seed(conn)
    summary = {"documents": 0, "versions": 0, "unchanged": 0, "updated": 0, "created": 0}
    for item in inventory:
        existing = conn.execute("SELECT * FROM task_registry_entries WHERE task_name = ?", (item.task_name,)).fetchone()
        latest_version = _existing_latest_version(conn, item.task_name) if existing else None
        payload = asdict(item)
        try:
            metadata_payload = json.loads(item.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata_payload = {}
        if isinstance(metadata_payload, dict):
            payload.update(metadata_payload)
        payload["source_path"] = item.source_path
        if latest_version and latest_version.get("source_sha256") == item.source_sha256:
            conn.execute(
                """
                INSERT INTO task_registry_entries (
                    task_name, job_id, session_target, platform_id, mode, model,
                    source_path, source_sha256, source_size_bytes, source_mtime,
                    current_version_id, latest_status, active, imported_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
                ON CONFLICT(task_name) DO UPDATE SET
                    job_id = excluded.job_id,
                    session_target = excluded.session_target,
                    platform_id = excluded.platform_id,
                    mode = excluded.mode,
                    model = excluded.model,
                    source_path = excluded.source_path,
                    source_sha256 = excluded.source_sha256,
                    source_size_bytes = excluded.source_size_bytes,
                    source_mtime = excluded.source_mtime,
                    current_version_id = excluded.current_version_id,
                    latest_status = excluded.latest_status,
                    active = excluded.active,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    item.task_name,
                    item.job_id,
                    item.session_target,
                    item.platform_id,
                    item.mode,
                    item.model,
                    item.source_path,
                    item.source_sha256,
                    item.source_size_bytes,
                    item.source_mtime,
                    latest_version["version_id"],
                    _now(),
                    _now(),
                    json.dumps({**payload, "current_version_id": latest_version["version_id"], "latest_status": "current"}, sort_keys=True),
                ),
            )
            summary["unchanged"] += 1
            summary["documents"] += 1
            continue

        version_number = 1
        if latest_version:
            version_number = int(latest_version["version_number"]) + 1
        version_id = f"{item.task_name}:v{version_number}"
        now = _now()
        conn.execute(
            """
            INSERT INTO task_registry_versions (
                version_id, task_name, version_number, state,
                job_id, session_target, platform_id, mode, model,
                source_path, source_sha256, source_size_bytes, source_mtime,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(version_id) DO UPDATE SET
                state = excluded.state,
                job_id = excluded.job_id,
                session_target = excluded.session_target,
                platform_id = excluded.platform_id,
                mode = excluded.mode,
                model = excluded.model,
                source_path = excluded.source_path,
                source_sha256 = excluded.source_sha256,
                source_size_bytes = excluded.source_size_bytes,
                source_mtime = excluded.source_mtime,
                author_id = excluded.author_id,
                change_summary = excluded.change_summary,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                version_id,
                item.task_name,
                version_number,
                "imported",
                item.job_id,
                item.session_target,
                item.platform_id,
                item.mode,
                item.model,
                item.source_path,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                None,
                "task registry sync",
                now,
                now,
                json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
            ),
        )
        conn.execute(
            """
            INSERT INTO task_registry_entries (
                task_name, job_id, session_target, platform_id, mode, model,
                source_path, source_sha256, source_size_bytes, source_mtime,
                current_version_id, latest_status, active, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
            ON CONFLICT(task_name) DO UPDATE SET
                job_id = excluded.job_id,
                session_target = excluded.session_target,
                platform_id = excluded.platform_id,
                mode = excluded.mode,
                model = excluded.model,
                source_path = excluded.source_path,
                source_sha256 = excluded.source_sha256,
                source_size_bytes = excluded.source_size_bytes,
                source_mtime = excluded.source_mtime,
                current_version_id = excluded.current_version_id,
                latest_status = excluded.latest_status,
                active = excluded.active,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                item.task_name,
                item.job_id,
                item.session_target,
                item.platform_id,
                item.mode,
                item.model,
                item.source_path,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                version_id,
                now,
                now,
                json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
            ),
        )
        summary["documents"] += 1
        summary["versions"] += 1
        summary["created" if not existing else "updated"] += 1
    return summary


def list_task_inventory(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM task_registry_entries
        ORDER BY COALESCE(platform_id, ''), mode, task_name
        """
    ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        try:
            payload = json.loads(record.get("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            if payload.get("sandbox_mode"):
                record["sandbox_mode"] = payload.get("sandbox_mode")
            if payload.get("sandbox_allowlist") is not None:
                record["sandbox_allowlist"] = payload.get("sandbox_allowlist")
        records.append(record)
    return records


def list_task_versions(conn: Any, task_name: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM task_registry_versions
        WHERE task_name = ?
        ORDER BY version_number DESC
        """,
        (task_name,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_task_registry_entry(conn: Any, task_name: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM task_registry_entries WHERE task_name = ?", (task_name,)).fetchone()
    if not row:
        return None
    payload = dict(row)
    try:
        payload_data = json.loads(payload.get("payload_json") or "{}")
    except json.JSONDecodeError:
        payload_data = {}
    if isinstance(payload_data, dict):
        if payload_data.get("sandbox_mode"):
            payload["sandbox_mode"] = payload_data.get("sandbox_mode")
        if payload_data.get("sandbox_allowlist") is not None:
            payload["sandbox_allowlist"] = payload_data.get("sandbox_allowlist")
    payload["versions"] = list_task_versions(conn, task_name)
    return payload


def get_task_registry_summary(conn: Any) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS count FROM task_registry_entries").fetchone()
    versions = conn.execute("SELECT COUNT(*) AS count FROM task_registry_versions").fetchone()
    by_platform_rows = conn.execute(
        """
        SELECT COALESCE(platform_id, 'global') AS platform_id, COUNT(*) AS count
        FROM task_registry_entries
        GROUP BY COALESCE(platform_id, 'global')
        ORDER BY platform_id
        """
    ).fetchall()
    return {
        "total_tools": int(total["count"] if total else 0),
        "total_versions": int(versions["count"] if versions else 0),
        "by_platform": [{"platform_id": row["platform_id"], "count": int(row["count"])} for row in by_platform_rows],
    }
