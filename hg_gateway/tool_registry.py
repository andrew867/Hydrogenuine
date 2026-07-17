from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SUPPORT_MODULE_NAMES = {"__init__.py", "base.py", "registry.py", "transport.py"}


@dataclass(frozen=True)
class ToolRegistryItem:
    tool_id: str
    tool_kind: str
    platform_id: str | None
    file_path: str
    module_path: str
    title: str
    description: str
    source_sha256: str
    source_size_bytes: int
    source_mtime: str
    metadata_json: str = "{}"


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _module_path_from_file(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def _platform_from_path(rel: Path) -> str | None:
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "hg_platforms":
        return parts[1]
    return None


def _tool_kind_from_path(rel: Path) -> str:
    return "support" if rel.name in SUPPORT_MODULE_NAMES else "script"


def _title_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip() or path.stem


def _description_from_text(path: Path, text: str) -> str:
    try:
        parsed = ast.parse(text)
        docstring = ast.get_docstring(parsed) or ""
    except SyntaxError:
        docstring = ""
    summary = " ".join(docstring.strip().split()).strip()
    if summary:
        return summary.split(".")[0].strip() or _title_from_path(path)
    return _title_from_path(path)


def discover_tool_files(root: Path | None = None) -> list[Path]:
    workspace = root or workspace_root()
    base = workspace / "hg_platforms"
    if not base.exists():
        return []
    files = [
        path
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    ]
    return sorted({path.resolve() for path in files}, key=lambda p: p.as_posix().lower())


def inventory_tool_registry(root: Path | None = None) -> list[ToolRegistryItem]:
    workspace = root or workspace_root()
    items: list[ToolRegistryItem] = []
    for path in discover_tool_files(workspace):
        rel_path = path.relative_to(workspace).as_posix()
        rel = Path(rel_path)
        content = _read_text(path)
        stat = path.stat()
        items.append(
            ToolRegistryItem(
                tool_id=_module_path_from_file(path, workspace),
                tool_kind=_tool_kind_from_path(rel),
                platform_id=_platform_from_path(rel),
                file_path=rel_path,
                module_path=_module_path_from_file(path, workspace),
                title=_title_from_path(path),
                description=_description_from_text(path, content),
                source_sha256=_hash_text(content),
                source_size_bytes=stat.st_size,
                source_mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                metadata_json=json.dumps(
                    {
                        "platform_id": _platform_from_path(rel),
                        "tool_kind": _tool_kind_from_path(rel),
                        "module_path": _module_path_from_file(path, workspace),
                    },
                    sort_keys=True,
                ),
            )
        )
    return items


def ensure_tool_registry_seed(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_registry_entries (
            tool_id TEXT PRIMARY KEY,
            tool_kind TEXT NOT NULL,
            platform_id TEXT,
            file_path TEXT NOT NULL UNIQUE,
            module_path TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
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
        CREATE TABLE IF NOT EXISTS tool_registry_versions (
            version_id TEXT PRIMARY KEY,
            tool_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'imported',
            file_path TEXT NOT NULL,
            module_path TEXT NOT NULL,
            tool_kind TEXT NOT NULL,
            platform_id TEXT,
            source_sha256 TEXT NOT NULL,
            source_size_bytes INTEGER NOT NULL,
            source_mtime TEXT,
            author_id TEXT,
            change_summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            UNIQUE(tool_id, version_number)
        )
        """
    )


def _existing_latest_version(conn: Any, tool_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT version_id, version_number, source_sha256
        FROM tool_registry_versions
        WHERE tool_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (tool_id,),
    ).fetchone()
    return dict(row) if row else None


def sync_tool_registry(conn: Any, items: Iterable[ToolRegistryItem] | None = None, root: Path | None = None) -> dict[str, Any]:
    inventory = list(items or inventory_tool_registry(root))
    ensure_tool_registry_seed(conn)
    summary = {
        "documents": 0,
        "versions": 0,
        "unchanged": 0,
        "updated": 0,
        "created": 0,
    }
    for item in inventory:
        existing = conn.execute("SELECT * FROM tool_registry_entries WHERE file_path = ?", (item.file_path,)).fetchone()
        latest_version = _existing_latest_version(conn, item.tool_id) if existing else None
        payload = {
            "tool_id": item.tool_id,
            "tool_kind": item.tool_kind,
            "platform_id": item.platform_id,
            "file_path": item.file_path,
            "module_path": item.module_path,
            "title": item.title,
            "description": item.description,
            "source_sha256": item.source_sha256,
            "source_size_bytes": item.source_size_bytes,
            "source_mtime": item.source_mtime,
        }
        if latest_version and latest_version.get("source_sha256") == item.source_sha256:
            conn.execute(
                """
                INSERT INTO tool_registry_entries (
                    tool_id, tool_kind, platform_id, file_path, module_path, title,
                    description, source_sha256, source_size_bytes, source_mtime,
                    current_version_id, latest_status, active, imported_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    tool_kind = excluded.tool_kind,
                    platform_id = excluded.platform_id,
                    module_path = excluded.module_path,
                    title = excluded.title,
                    description = excluded.description,
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
                    item.tool_id,
                    item.tool_kind,
                    item.platform_id,
                    item.file_path,
                    item.module_path,
                    item.title,
                    item.description,
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
        version_id = f"{item.tool_id}:v{version_number}"
        now = _now()
        conn.execute(
            """
            INSERT INTO tool_registry_versions (
                version_id, tool_id, version_number, state,
                file_path, module_path, tool_kind, platform_id,
                source_sha256, source_size_bytes, source_mtime,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(version_id) DO UPDATE SET
                state = excluded.state,
                file_path = excluded.file_path,
                module_path = excluded.module_path,
                tool_kind = excluded.tool_kind,
                platform_id = excluded.platform_id,
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
                item.tool_id,
                version_number,
                "imported",
                item.file_path,
                item.module_path,
                item.tool_kind,
                item.platform_id,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                None,
                "tool registry sync",
                now,
                now,
                json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
            ),
        )
        conn.execute(
            """
            INSERT INTO tool_registry_entries (
                tool_id, tool_kind, platform_id, file_path, module_path, title,
                description, source_sha256, source_size_bytes, source_mtime,
                current_version_id, latest_status, active, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                tool_kind = excluded.tool_kind,
                platform_id = excluded.platform_id,
                module_path = excluded.module_path,
                title = excluded.title,
                description = excluded.description,
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
                item.tool_id,
                item.tool_kind,
                item.platform_id,
                item.file_path,
                item.module_path,
                item.title,
                item.description,
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


def list_tool_inventory(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM tool_registry_entries
        ORDER BY COALESCE(platform_id, ''), file_path
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_tool_versions(conn: Any, tool_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM tool_registry_versions
        WHERE tool_id = ?
        ORDER BY version_number DESC
        """,
        (tool_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_tool_registry_entry(conn: Any, tool_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM tool_registry_entries WHERE tool_id = ?",
        (tool_id,),
    ).fetchone()
    if not row:
        return None
    payload = dict(row)
    payload["versions"] = list_tool_versions(conn, tool_id)
    return payload


def get_tool_registry_summary(conn: Any) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS count FROM tool_registry_entries").fetchone()
    versions = conn.execute("SELECT COUNT(*) AS count FROM tool_registry_versions").fetchone()
    by_kind_rows = conn.execute(
        """
        SELECT tool_kind, COUNT(*) AS count
        FROM tool_registry_entries
        GROUP BY tool_kind
        ORDER BY tool_kind
        """
    ).fetchall()
    return {
        "total_tools": int(total["count"] if total else 0),
        "total_versions": int(versions["count"] if versions else 0),
        "by_kind": [{"tool_kind": row["tool_kind"], "count": int(row["count"])} for row in by_kind_rows],
    }
