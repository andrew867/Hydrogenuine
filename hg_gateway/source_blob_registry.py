from __future__ import annotations

import difflib
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SOURCE_BLOB_ROOT = Path("hg_platforms")


@dataclass(frozen=True)
class SourceBlobClassDefinition:
    class_key: str
    title: str
    root_path: str
    glob_pattern: str
    description: str
    editable: bool = True
    versioned: bool = True
    import_required: bool = True
    archive_policy: str = "archive-on-supersede"
    metadata_json: str = "{}"


@dataclass(frozen=True)
class SourceBlobInventoryItem:
    source_blob_id: str
    class_key: str
    title: str
    file_path: str
    module_path: str
    source_sha256: str
    source_size_bytes: int
    source_mtime: str
    source_text: str
    line_count: int
    word_count: int
    editable: bool = True
    versioned: bool = True
    import_required: bool = True
    archive_policy: str = "archive-on-supersede"
    payload_json: str = "{}"


SOURCE_BLOB_CLASS_DEFINITIONS: tuple[SourceBlobClassDefinition, ...] = (
    SourceBlobClassDefinition(
        class_key="python_source",
        title="Python source blobs",
        root_path="hg_platforms",
        glob_pattern="**/*.py",
        description="Executable Python source modules for live platform integrations and runtime entrypoints.",
        metadata_json='{"editable":"yes","versioning":"required","source":"hg_platforms"}',
    ),
)


def workspace_root() -> Path:
    configured = os.getenv("HG_WORKSPACE")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_rel_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _module_path_from_file(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def _title_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip() or path.stem


def discover_source_blob_files(root: Path | None = None) -> list[Path]:
    workspace = root or workspace_root()
    base = workspace / SOURCE_BLOB_ROOT
    if not base.exists():
        return []
    files = [
        path
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    ]
    return sorted({path.resolve() for path in files}, key=lambda p: p.as_posix().lower())


def inventory_source_blobs(root: Path | None = None) -> list[SourceBlobInventoryItem]:
    workspace = root or workspace_root()
    items: list[SourceBlobInventoryItem] = []
    for path in discover_source_blob_files(workspace):
        rel_path = _normalize_rel_path(path, workspace)
        content = _read_text(path)
        stat = path.stat()
        items.append(
            SourceBlobInventoryItem(
                source_blob_id=f"python_source:{rel_path}",
                class_key="python_source",
                title=_title_from_path(path),
                file_path=rel_path,
                module_path=_module_path_from_file(path, workspace),
                source_sha256=_hash_text(content),
                source_size_bytes=stat.st_size,
                source_mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                source_text=content,
                line_count=content.count("\n") + (1 if content else 0),
                word_count=len(content.split()),
                payload_json=json.dumps(
                    {
                        "source_blob_id": f"python_source:{rel_path}",
                        "class_key": "python_source",
                        "file_path": rel_path,
                        "module_path": _module_path_from_file(path, workspace),
                        "editable": True,
                        "versioned": True,
                        "import_required": True,
                        "archive_policy": "archive-on-supersede",
                    },
                    sort_keys=True,
                ),
            )
        )
    return items


def ensure_source_blob_registry_seed(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_blob_classes (
            class_key TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            root_path TEXT NOT NULL,
            glob_pattern TEXT NOT NULL,
            description TEXT NOT NULL,
            editable INTEGER NOT NULL DEFAULT 1,
            versioned INTEGER NOT NULL DEFAULT 1,
            import_required INTEGER NOT NULL DEFAULT 1,
            archive_policy TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_blob_entries (
            source_blob_id TEXT PRIMARY KEY,
            class_key TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            module_path TEXT NOT NULL,
            title TEXT NOT NULL,
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_entries_class ON source_blob_entries(class_key, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_entries_status ON source_blob_entries(latest_status, updated_at DESC)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_blob_versions (
            version_id TEXT PRIMARY KEY,
            source_blob_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'imported',
            source_text TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            file_path TEXT NOT NULL,
            module_path TEXT NOT NULL,
            author_id TEXT,
            change_summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            UNIQUE(source_blob_id, version_number)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_versions_blob ON source_blob_versions(source_blob_id, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_versions_created ON source_blob_versions(created_at DESC)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_blob_runs (
            run_id TEXT PRIMARY KEY,
            source_blob_id TEXT NOT NULL,
            module_path TEXT NOT NULL,
            entrypoint TEXT,
            args_json TEXT NOT NULL DEFAULT '[]',
            command_json TEXT NOT NULL,
            workspace_root TEXT NOT NULL,
            sandbox_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            returncode INTEGER,
            stdout TEXT,
            stderr TEXT,
            actor_id TEXT,
            change_summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_runs_blob ON source_blob_runs(source_blob_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_runs_status ON source_blob_runs(status, created_at DESC)")
    for class_def in SOURCE_BLOB_CLASS_DEFINITIONS:
        conn.execute(
            """
            INSERT INTO source_blob_classes (
                class_key, title, root_path, glob_pattern, description,
                editable, versioned, import_required, archive_policy,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(class_key) DO NOTHING
            """,
            (
                class_def.class_key,
                class_def.title,
                class_def.root_path,
                class_def.glob_pattern,
                class_def.description,
                int(class_def.editable),
                int(class_def.versioned),
                int(class_def.import_required),
                class_def.archive_policy,
                class_def.metadata_json,
                _now(),
                _now(),
            ),
        )


def _existing_latest_version(conn: Any, source_blob_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT version_id, version_number, source_sha256
        FROM source_blob_versions
        WHERE source_blob_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (source_blob_id,),
    ).fetchone()
    return dict(row) if row else None


def sync_source_blob_inventory(conn: Any, items: Iterable[SourceBlobInventoryItem] | None = None, root: Path | None = None) -> dict[str, Any]:
    inventory = list(items or inventory_source_blobs(root))
    ensure_source_blob_registry_seed(conn)
    summary = {"classes": len(SOURCE_BLOB_CLASS_DEFINITIONS), "documents": 0, "versions": 0, "unchanged": 0, "updated": 0, "created": 0}
    for item in inventory:
        existing = conn.execute("SELECT * FROM source_blob_entries WHERE file_path = ?", (item.file_path,)).fetchone()
        latest_version = _existing_latest_version(conn, item.source_blob_id) if existing else None
        payload = {
            "source_blob_id": item.source_blob_id,
            "class_key": item.class_key,
            "title": item.title,
            "file_path": item.file_path,
            "module_path": item.module_path,
            "source_sha256": item.source_sha256,
            "source_size_bytes": item.source_size_bytes,
            "source_mtime": item.source_mtime,
            "editable": item.editable,
            "versioned": item.versioned,
            "import_required": item.import_required,
            "archive_policy": item.archive_policy,
        }
        if latest_version and latest_version.get("source_sha256") == item.source_sha256:
            conn.execute(
                """
                INSERT INTO source_blob_entries (
                    source_blob_id, class_key, file_path, module_path, title,
                    source_sha256, source_size_bytes, source_mtime, current_version_id,
                    latest_status, active, imported_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    class_key = excluded.class_key,
                    module_path = excluded.module_path,
                    title = excluded.title,
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
                    item.source_blob_id,
                    item.class_key,
                    item.file_path,
                    item.module_path,
                    item.title,
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
            conn.commit()
            continue

        version_number = 1
        if latest_version:
            version_number = int(latest_version["version_number"]) + 1
        version_id = f"{item.source_blob_id}:v{version_number}"
        now = _now()
        conn.execute(
            """
            INSERT INTO source_blob_versions (
                version_id, source_blob_id, version_number, state,
                source_text, source_sha256, file_path, module_path,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(version_id) DO UPDATE SET
                state = excluded.state,
                source_text = excluded.source_text,
                source_sha256 = excluded.source_sha256,
                file_path = excluded.file_path,
                module_path = excluded.module_path,
                author_id = excluded.author_id,
                change_summary = excluded.change_summary,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                version_id,
                item.source_blob_id,
                version_number,
                "imported",
                item.source_text,
                item.source_sha256,
                item.file_path,
                item.module_path,
                None,
                "source blob inventory sync",
                now,
                now,
                json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
            ),
        )
        conn.execute(
            """
            INSERT INTO source_blob_entries (
                source_blob_id, class_key, file_path, module_path, title,
                source_sha256, source_size_bytes, source_mtime, current_version_id,
                latest_status, active, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                class_key = excluded.class_key,
                module_path = excluded.module_path,
                title = excluded.title,
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
                item.source_blob_id,
                item.class_key,
                item.file_path,
                item.module_path,
                item.title,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                version_id,
                _now(),
                _now(),
                json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
            ),
        )
        summary["documents"] += 1
        summary["versions"] += 1
        summary["created" if not existing else "updated"] += 1
        conn.commit()
    return summary


def list_source_blob_inventory(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT d.*, c.title AS class_title, c.description AS class_description, c.root_path AS class_root_path
        FROM source_blob_entries d
        LEFT JOIN source_blob_classes c ON c.class_key = d.class_key
        ORDER BY d.class_key, d.file_path
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_source_blob_inventory_summary(conn: Any) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS count FROM source_blob_entries").fetchone()
    versions = conn.execute("SELECT COUNT(*) AS count FROM source_blob_versions").fetchone()
    by_class_rows = conn.execute(
        """
        SELECT class_key, COUNT(*) AS count
        FROM source_blob_entries
        GROUP BY class_key
        ORDER BY class_key
        """
    ).fetchall()
    return {
        "total_documents": int(total["count"] if total else 0),
        "total_versions": int(versions["count"] if versions else 0),
        "by_class": [{"class_key": row["class_key"], "count": int(row["count"])} for row in by_class_rows],
        "classes": [asdict(class_def) for class_def in SOURCE_BLOB_CLASS_DEFINITIONS],
    }


def list_source_blob_versions(conn: Any, source_blob_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM source_blob_versions
        WHERE source_blob_id = ?
        ORDER BY version_number DESC
        """,
        (source_blob_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_source_blob_document(conn: Any, source_blob_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT d.*, c.title AS class_title, c.description AS class_description, c.root_path AS class_root_path,
               c.glob_pattern AS class_glob_pattern, c.archive_policy AS class_archive_policy
        FROM source_blob_entries d
        LEFT JOIN source_blob_classes c ON c.class_key = d.class_key
        WHERE d.source_blob_id = ?
        """,
        (source_blob_id,),
    ).fetchone()
    if not row:
        return None
    payload = dict(row)
    payload["versions"] = list_source_blob_versions(conn, source_blob_id)
    payload["runs"] = list_source_blob_runs(conn, source_blob_id)
    workspace_path = _source_blob_workspace_path(payload["file_path"])
    payload["workspace_path"] = str(workspace_path)
    payload["vscode_uri"] = f"vscode://file/{workspace_path.as_posix()}"
    return payload


def list_source_blob_runs(conn: Any, source_blob_id: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM source_blob_runs
        WHERE source_blob_id = ?
        ORDER BY created_at DESC, run_id DESC
        LIMIT ?
        """,
        (source_blob_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _source_blob_workspace_path(file_path: str, root: Path | None = None) -> Path:
    workspace = root or workspace_root()
    relative = Path(file_path)
    if relative.is_absolute():
        raise ValueError(f"Source blob file_path must be relative: {file_path}")
    if relative.parts and relative.parts[0] == "..":
        raise ValueError(f"Source blob file_path escapes workspace: {file_path}")
    return (workspace / relative).resolve()


def _write_source_blob_file(file_path: str, source_text: str, root: Path | None = None) -> None:
    target = _source_blob_workspace_path(file_path, root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source_text, encoding="utf-8")


def _source_blob_class_row(conn: Any, class_key: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT *
        FROM source_blob_classes
        WHERE class_key = ?
        """,
        (class_key,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown source blob class: {class_key}")
    return dict(row)


def _source_blob_latest_version(conn: Any, source_blob_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM source_blob_versions
        WHERE source_blob_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (source_blob_id,),
    ).fetchone()
    return dict(row) if row else None


def _source_blob_version_text(version_row: dict[str, Any] | None) -> str:
    if not version_row:
        return ""
    return str(version_row.get("source_text") or "")


def create_source_blob_document(
    conn: Any,
    class_key: str,
    file_path: str,
    source_text: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    class_row = _source_blob_class_row(conn, class_key)
    if class_key != "python_source":
        raise ValueError(f"Unsupported source blob class for CRUD: {class_key}")
    if not file_path.startswith(f"{class_row['root_path']}/"):
        raise ValueError(f"Source blob file_path must live under {class_row['root_path']}: {file_path}")
    existing = conn.execute("SELECT 1 FROM source_blob_entries WHERE file_path = ?", (file_path,)).fetchone()
    if existing is not None:
        raise ValueError(f"Source blob already exists at file_path: {file_path}")
    source_blob_id = f"{class_key}:{file_path}"
    now = _now()
    next_title = title or _title_from_path(Path(file_path))
    source_hash = _hash_text(source_text)
    version_id = f"{source_blob_id}:v1"
    payload = {
        "source_blob_id": source_blob_id,
        "class_key": class_key,
        "title": next_title,
        "file_path": file_path,
        "module_path": _module_path_from_file(_source_blob_workspace_path(file_path, root=root), root or workspace_root()),
        "source_sha256": source_hash,
        "source_size_bytes": len(source_text.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(class_row["editable"]),
        "versioned": bool(class_row["versioned"]),
        "import_required": bool(class_row["import_required"]),
        "archive_policy": class_row["archive_policy"],
    }
    _write_source_blob_file(file_path, source_text, root=root)
    conn.execute(
        """
        INSERT INTO source_blob_versions (
            version_id, source_blob_id, version_number, state,
            source_text, source_sha256, file_path, module_path,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            source_blob_id,
            "published",
            source_text,
            source_hash,
            file_path,
            payload["module_path"],
            actor_id,
            change_summary or "created via source blob registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": 1}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        INSERT INTO source_blob_entries (
            source_blob_id, class_key, file_path, module_path, title,
            source_sha256, source_size_bytes, source_mtime, current_version_id,
            latest_status, active, imported_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', 1, ?, ?, ?)
        """,
        (
            source_blob_id,
            class_key,
            file_path,
            payload["module_path"],
            next_title,
            source_hash,
            payload["source_size_bytes"],
            now,
            version_id,
            now,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
        ),
    )
    return get_source_blob_document(conn, source_blob_id) or payload


def save_source_blob_document(
    conn: Any,
    source_blob_id: str,
    source_text: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    doc = get_source_blob_document(conn, source_blob_id)
    if doc is None:
        raise ValueError(f"Unknown source_blob_id: {source_blob_id}")
    if doc.get("class_key") != "python_source":
        raise ValueError(f"Unsupported source blob class for CRUD: {doc.get('class_key')}")
    existing_versions = len(doc.get("versions") or [])
    version_number = existing_versions + 1
    version_id = f"{source_blob_id}:v{version_number}"
    source_hash = _hash_text(source_text)
    now = _now()
    next_title = title or doc.get("title") or _title_from_path(Path(doc["file_path"]))
    payload = {
        "source_blob_id": source_blob_id,
        "class_key": doc["class_key"],
        "title": next_title,
        "file_path": doc["file_path"],
        "module_path": doc["module_path"],
        "source_sha256": source_hash,
        "source_size_bytes": len(source_text.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(doc.get("editable", 1)),
        "versioned": bool(doc.get("versioned", 1)),
        "import_required": bool(doc.get("import_required", 1)),
        "archive_policy": doc.get("archive_policy") or "archive-on-supersede",
    }
    _write_source_blob_file(doc["file_path"], source_text, root=root)
    conn.execute(
        """
        INSERT INTO source_blob_versions (
            version_id, source_blob_id, version_number, state,
            source_text, source_sha256, file_path, module_path,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            source_blob_id,
            version_number,
            "published",
            source_text,
            source_hash,
            doc["file_path"],
            doc["module_path"],
            actor_id,
            change_summary or "saved via source blob registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE source_blob_entries
        SET title = ?,
            source_sha256 = ?,
            source_size_bytes = ?,
            source_mtime = ?,
            current_version_id = ?,
            latest_status = 'current',
            active = 1,
            updated_at = ?,
            payload_json = ?
        WHERE source_blob_id = ?
        """,
        (
            next_title,
            source_hash,
            payload["source_size_bytes"],
            now,
            version_id,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
            source_blob_id,
        ),
    )
    return get_source_blob_document(conn, source_blob_id) or payload


def archive_source_blob_document(
    conn: Any,
    source_blob_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    doc = get_source_blob_document(conn, source_blob_id)
    if doc is None:
        raise ValueError(f"Unknown source_blob_id: {source_blob_id}")
    latest_version = _source_blob_latest_version(conn, source_blob_id)
    source_text = _source_blob_version_text(latest_version)
    if not source_text:
        raise ValueError(f"Cannot archive empty source blob: {source_blob_id}")
    version_number = len(doc.get("versions") or []) + 1
    version_id = f"{source_blob_id}:v{version_number}"
    now = _now()
    source_hash = _hash_text(source_text)
    payload = {
        "source_blob_id": source_blob_id,
        "class_key": doc["class_key"],
        "title": doc["title"],
        "file_path": doc["file_path"],
        "module_path": doc["module_path"],
        "source_sha256": source_hash,
        "source_size_bytes": len(source_text.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(doc.get("editable", 1)),
        "versioned": bool(doc.get("versioned", 1)),
        "import_required": bool(doc.get("import_required", 1)),
        "archive_policy": doc.get("archive_policy") or "archive-on-supersede",
    }
    conn.execute(
        """
        INSERT INTO source_blob_versions (
            version_id, source_blob_id, version_number, state,
            source_text, source_sha256, file_path, module_path,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            source_blob_id,
            version_number,
            "archived",
            source_text,
            source_hash,
            doc["file_path"],
            doc["module_path"],
            actor_id,
            change_summary or "archived via source blob registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": version_number, "latest_status": "archived"}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE source_blob_entries
        SET latest_status = 'archived',
            active = 0,
            current_version_id = ?,
            updated_at = ?,
            payload_json = ?
        WHERE source_blob_id = ?
        """,
        (
            version_id,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "archived"}, sort_keys=True),
            source_blob_id,
        ),
    )
    return get_source_blob_document(conn, source_blob_id) or payload


def restore_source_blob_document(
    conn: Any,
    source_blob_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    doc = get_source_blob_document(conn, source_blob_id)
    if doc is None:
        raise ValueError(f"Unknown source_blob_id: {source_blob_id}")
    latest_version = _source_blob_latest_version(conn, source_blob_id)
    source_text = _source_blob_version_text(latest_version)
    if not source_text:
        raise ValueError(f"Cannot restore empty source blob: {source_blob_id}")
    version_number = len(doc.get("versions") or []) + 1
    version_id = f"{source_blob_id}:v{version_number}"
    now = _now()
    source_hash = _hash_text(source_text)
    payload = {
        "source_blob_id": source_blob_id,
        "class_key": doc["class_key"],
        "title": doc["title"],
        "file_path": doc["file_path"],
        "module_path": doc["module_path"],
        "source_sha256": source_hash,
        "source_size_bytes": len(source_text.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(doc.get("editable", 1)),
        "versioned": bool(doc.get("versioned", 1)),
        "import_required": bool(doc.get("import_required", 1)),
        "archive_policy": doc.get("archive_policy") or "archive-on-supersede",
    }
    conn.execute(
        """
        INSERT INTO source_blob_versions (
            version_id, source_blob_id, version_number, state,
            source_text, source_sha256, file_path, module_path,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            source_blob_id,
            version_number,
            "restored",
            source_text,
            source_hash,
            doc["file_path"],
            doc["module_path"],
            actor_id,
            change_summary or "restored via source blob registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": version_number, "latest_status": "current"}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE source_blob_entries
        SET latest_status = 'current',
            active = 1,
            current_version_id = ?,
            updated_at = ?,
            payload_json = ?
        WHERE source_blob_id = ?
        """,
        (
            version_id,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
            source_blob_id,
        ),
    )
    return get_source_blob_document(conn, source_blob_id) or payload


def compare_source_blob_versions(
    conn: Any,
    source_blob_id: str,
    left_version_id: str | None = None,
    right_version_id: str | None = None,
) -> dict[str, Any] | None:
    versions = list_source_blob_versions(conn, source_blob_id)
    if not versions:
        return None
    version_by_id = {row["version_id"]: row for row in versions}
    left = version_by_id.get(left_version_id) if left_version_id else versions[1] if len(versions) > 1 else versions[0]
    right = version_by_id.get(right_version_id) if right_version_id else versions[0]
    if left is None or right is None:
        return None
    left_text = _source_blob_version_text(left)
    right_text = _source_blob_version_text(right)
    diff_lines = list(
        difflib.unified_diff(
            left_text.splitlines(keepends=True),
            right_text.splitlines(keepends=True),
            fromfile=f"{source_blob_id}@{left['version_number']}",
            tofile=f"{source_blob_id}@{right['version_number']}",
        )
    )
    return {
        "source_blob_id": source_blob_id,
        "left_version": {k: left.get(k) for k in ("version_id", "version_number", "state", "created_at", "change_summary")},
        "right_version": {k: right.get(k) for k in ("version_id", "version_number", "state", "created_at", "change_summary")},
        "diff_text": "".join(diff_lines),
        "diff_line_count": len(diff_lines),
        "left_source_text": left_text,
        "right_source_text": right_text,
    }


def record_source_blob_run(
    conn: Any,
    *,
    run_id: str,
    source_blob_id: str,
    module_path: str,
    entrypoint: str | None,
    args: list[str],
    command: list[str],
    workspace_root: str,
    sandbox_id: str | None,
    status: str,
    returncode: int | None,
    stdout: str | None,
    stderr: str | None,
    actor_id: str | None = None,
    change_summary: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_source_blob_registry_seed(conn)
    now = _now()
    payload_json = json.dumps(
        {
            "run_id": run_id,
            "source_blob_id": source_blob_id,
            "module_path": module_path,
            "entrypoint": entrypoint,
            "args": args,
            "command": command,
            "workspace_root": workspace_root,
            "sandbox_id": sandbox_id,
            "status": status,
            "returncode": returncode,
            **(payload or {}),
        },
        sort_keys=True,
    )
    conn.execute(
        """
        INSERT INTO source_blob_runs (
            run_id, source_blob_id, module_path, entrypoint, args_json, command_json,
            workspace_root, sandbox_id, status, returncode, stdout, stderr,
            actor_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            module_path = excluded.module_path,
            entrypoint = excluded.entrypoint,
            args_json = excluded.args_json,
            command_json = excluded.command_json,
            workspace_root = excluded.workspace_root,
            sandbox_id = excluded.sandbox_id,
            status = excluded.status,
            returncode = excluded.returncode,
            stdout = excluded.stdout,
            stderr = excluded.stderr,
            actor_id = excluded.actor_id,
            change_summary = excluded.change_summary,
            updated_at = excluded.updated_at,
            payload_json = excluded.payload_json
        """,
        (
            run_id,
            source_blob_id,
            module_path,
            entrypoint,
            json.dumps(args, sort_keys=True),
            json.dumps(command, sort_keys=True),
            workspace_root,
            sandbox_id,
            status,
            returncode,
            stdout,
            stderr,
            actor_id,
            change_summary,
            now,
            now,
            payload_json,
        ),
    )
    row = conn.execute("SELECT * FROM source_blob_runs WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else {
        "run_id": run_id,
        "source_blob_id": source_blob_id,
        "module_path": module_path,
        "entrypoint": entrypoint,
        "args_json": json.dumps(args, sort_keys=True),
        "command_json": json.dumps(command, sort_keys=True),
        "workspace_root": workspace_root,
        "sandbox_id": sandbox_id,
        "status": status,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "actor_id": actor_id,
        "change_summary": change_summary,
        "created_at": now,
        "updated_at": now,
        "payload_json": payload_json,
    }
