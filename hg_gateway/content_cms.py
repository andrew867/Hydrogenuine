from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


CONTENT_CLASS_ORDER = ("task", "skill", "plan", "runbook", "persona_meta")
CONTENT_EXCLUDED_SKILL_PARTS = {"tests", "__pycache__", ".audit", ".backups", "backups", "task-file-backups"}
PERSONA_META_FILENAMES = {"SOUL.md", "HEART.md", "IDENTITY.md", "MEMORY.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md"}


@dataclass(frozen=True)
class ContentClassDefinition:
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
class ContentInventoryItem:
    content_id: str
    class_key: str
    title: str
    file_path: str
    source_sha256: str
    source_size_bytes: int
    source_mtime: str
    content_markdown: str
    line_count: int
    word_count: int
    editable: bool = True
    versioned: bool = True
    import_required: bool = True
    archive_policy: str = "archive-on-supersede"


CONTENT_CLASS_DEFINITIONS: tuple[ContentClassDefinition, ...] = (
    ContentClassDefinition(
        class_key="task",
        title="Automation task files",
        root_path="skills/automation/tasks",
        glob_pattern="**/*.md",
        description="Operator task instructions executed by the automation runtime and job registry.",
        metadata_json='{"editable":"yes","versioning":"required","source":"skills/automation/tasks"}',
    ),
    ContentClassDefinition(
        class_key="skill",
        title="Automation skill docs",
        root_path="skills/automation",
        glob_pattern="**/*.md",
        description="Skill and runbook docs that shape automation behavior and operator guidance.",
        metadata_json='{"editable":"yes","versioning":"required","source":"skills/automation"}',
    ),
    ContentClassDefinition(
        class_key="plan",
        title="Plan docs",
        root_path=".cursor/plans",
        glob_pattern="**/*.md",
        description="Execution plans, tranche specs, and roadmap docs that operators edit in-browser.",
        metadata_json='{"editable":"yes","versioning":"required","source":".cursor/plans"}',
    ),
    ContentClassDefinition(
        class_key="runbook",
        title="Runbooks",
        root_path="docs/runbooks",
        glob_pattern="**/*.md",
        description="Operational and support runbooks that should be editable without leaving the browser.",
        metadata_json='{"editable":"yes","versioning":"required","source":"docs/runbooks"}',
    ),
    ContentClassDefinition(
        class_key="persona_meta",
        title="Persona and operator meta docs",
        root_path=".",
        glob_pattern="SOUL.md, HEART.md, IDENTITY.md, MEMORY.md, AGENTS.md, TOOLS.md, HEARTBEAT.md",
        description="Persona, memory, identity, and operator meta docs used to steer the runtime and console.",
        metadata_json='{"editable":"yes","versioning":"required","source":"workspace-root-and-personas"}',
    ),
)


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_rel_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_document_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for key in ("editable", "versioned", "import_required", "archived"):
        if key in normalized and normalized[key] is not None:
            normalized[key] = bool(normalized[key])
    return normalized


def _read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _title_from_markdown(path: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or path.stem
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.stem


def _is_task_path(rel: Path) -> bool:
    return "tasks" in rel.parts and rel.parts[0] == "skills" and rel.parts[1] == "automation"


def _is_skill_path(rel: Path) -> bool:
    if rel.parts[:2] != ("skills", "automation"):
        return False
    if "archive" in rel.parts or "tasks" in rel.parts or "personas" in rel.parts:
        return False
    return not any(part in CONTENT_EXCLUDED_SKILL_PARTS for part in rel.parts)


def _is_plan_path(rel: Path) -> bool:
    return rel.parts[:2] == (".cursor", "plans") and "archive" not in rel.parts


def _is_runbook_path(rel: Path) -> bool:
    return rel.parts[:2] == ("docs", "runbooks")


def _is_persona_meta_path(rel: Path) -> bool:
    if rel.name not in PERSONA_META_FILENAMES:
        return False
    if rel.parts[:2] == ("skills", "automation") and "personas" in rel.parts:
        return True
    return len(rel.parts) == 1


def classify_content_path(rel_path: str) -> str | None:
    rel = Path(rel_path)
    if _is_task_path(rel):
        return "task"
    if _is_skill_path(rel):
        return "skill"
    if _is_plan_path(rel):
        return "plan"
    if _is_runbook_path(rel):
        return "runbook"
    if _is_persona_meta_path(rel):
        return "persona_meta"
    return None


def discover_content_files(root: Path | None = None) -> list[Path]:
    workspace = root or workspace_root()
    candidates: list[Path] = []
    for rel in (
        Path("skills/automation"),
        Path("skills/automation/personas"),
        Path(".cursor/plans"),
        Path("docs/runbooks"),
    ):
        base = workspace / rel
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            rel_path = path.relative_to(workspace)
            class_key = classify_content_path(rel_path.as_posix())
            if class_key is None:
                continue
            candidates.append(path)
    for filename in PERSONA_META_FILENAMES:
        path = workspace / filename
        if path.exists():
            candidates.append(path)
    return sorted({path.resolve() for path in candidates}, key=lambda p: p.as_posix().lower())


def inventory_content(root: Path | None = None) -> list[ContentInventoryItem]:
    workspace = root or workspace_root()
    items: list[ContentInventoryItem] = []
    for path in discover_content_files(workspace):
        rel_path = _normalize_rel_path(path, workspace)
        class_key = classify_content_path(rel_path)
        if class_key is None:
            continue
        content = _read_markdown(path)
        title = _title_from_markdown(path, content)
        text_hash = _hash_text(content)
        stat = path.stat()
        items.append(
            ContentInventoryItem(
                content_id=f"{class_key}:{rel_path}",
                class_key=class_key,
                title=title,
                file_path=rel_path,
                source_sha256=text_hash,
                source_size_bytes=stat.st_size,
                source_mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                content_markdown=content,
                line_count=content.count("\n") + (1 if content else 0),
                word_count=len(content.split()),
            )
        )
    return items


def ensure_content_registry_seed(conn: Any) -> None:
    for class_def in CONTENT_CLASS_DEFINITIONS:
        conn.execute(
            """
            INSERT INTO content_document_classes (
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


def _existing_latest_version(conn: Any, content_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT version_id, version_number, content_sha256
        FROM content_document_versions
        WHERE content_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (content_id,),
    ).fetchone()
    return dict(row) if row else None


def sync_content_inventory(conn: Any, items: Iterable[ContentInventoryItem] | None = None, root: Path | None = None) -> dict[str, Any]:
    inventory = list(items or inventory_content(root))
    ensure_content_registry_seed(conn)
    summary = {
        "classes": len(CONTENT_CLASS_DEFINITIONS),
        "documents": 0,
        "versions": 0,
        "unchanged": 0,
        "updated": 0,
        "created": 0,
    }
    for item in inventory:
        existing = conn.execute(
            "SELECT * FROM content_documents WHERE file_path = ?",
            (item.file_path,),
        ).fetchone()
        latest_version = _existing_latest_version(conn, item.content_id) if existing else None
        payload = {
            "content_id": item.content_id,
            "class_key": item.class_key,
            "title": item.title,
            "file_path": item.file_path,
            "source_sha256": item.source_sha256,
            "source_size_bytes": item.source_size_bytes,
            "source_mtime": item.source_mtime,
            "editable": item.editable,
            "versioned": item.versioned,
            "import_required": item.import_required,
            "archive_policy": item.archive_policy,
        }
        if latest_version and latest_version.get("content_sha256") == item.source_sha256:
            conn.execute(
                """
                INSERT INTO content_documents (
                    content_id, class_key, file_path, title, current_version_id,
                    source_sha256, source_size_bytes, source_mtime, editable,
                    archived, latest_status, imported_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'current', ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    class_key = excluded.class_key,
                    title = excluded.title,
                    current_version_id = excluded.current_version_id,
                    source_sha256 = excluded.source_sha256,
                    source_size_bytes = excluded.source_size_bytes,
                    source_mtime = excluded.source_mtime,
                    editable = excluded.editable,
                    archived = excluded.archived,
                    latest_status = excluded.latest_status,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    item.content_id,
                    item.class_key,
                    item.file_path,
                    item.title,
                    latest_version["version_id"],
                    item.source_sha256,
                    item.source_size_bytes,
                    item.source_mtime,
                    int(item.editable),
                    _now(),
                    _now(),
                    json.dumps(payload, sort_keys=True),
                ),
            )
            summary["unchanged"] += 1
            summary["documents"] += 1
            continue

        version_number = 1
        if latest_version:
            version_number = int(latest_version["version_number"]) + 1
        version_id = f"{item.content_id}:v{version_number}"
        conn.execute(
            """
            INSERT INTO content_document_versions (
                version_id, content_id, version_number, state,
                content_markdown, content_sha256, source_path, source_sha256,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(version_id) DO UPDATE SET
                state = excluded.state,
                content_markdown = excluded.content_markdown,
                content_sha256 = excluded.content_sha256,
                source_path = excluded.source_path,
                source_sha256 = excluded.source_sha256,
                author_id = excluded.author_id,
                change_summary = excluded.change_summary,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                version_id,
                item.content_id,
                version_number,
                "imported",
                item.content_markdown,
                item.source_sha256,
                item.file_path,
                item.source_sha256,
                None,
                "content inventory sync",
                _now(),
                _now(),
                json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
            ),
        )
        conn.execute(
            """
            INSERT INTO content_documents (
                content_id, class_key, file_path, title, current_version_id,
                source_sha256, source_size_bytes, source_mtime, editable,
                archived, latest_status, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'current', ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                class_key = excluded.class_key,
                title = excluded.title,
                current_version_id = excluded.current_version_id,
                source_sha256 = excluded.source_sha256,
                source_size_bytes = excluded.source_size_bytes,
                source_mtime = excluded.source_mtime,
                editable = excluded.editable,
                archived = excluded.archived,
                latest_status = excluded.latest_status,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                item.content_id,
                item.class_key,
                item.file_path,
                item.title,
                version_id,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                int(item.editable),
                _now(),
                _now(),
                json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
            ),
        )
        summary["documents"] += 1
        summary["versions"] += 1
        summary["created" if not existing else "updated"] += 1
    return summary


def list_content_inventory(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT d.*, c.title AS class_title, c.description AS class_description, c.root_path AS class_root_path
        FROM content_documents d
        LEFT JOIN content_document_classes c ON c.class_key = d.class_key
        ORDER BY d.class_key, d.file_path
        """
    ).fetchall()
    return [_normalize_document_payload(dict(row)) for row in rows]


def get_content_inventory_summary(conn: Any) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS count FROM content_documents").fetchone()
    versions = conn.execute("SELECT COUNT(*) AS count FROM content_document_versions").fetchone()
    by_class_rows = conn.execute(
        """
        SELECT class_key, COUNT(*) AS count
        FROM content_documents
        GROUP BY class_key
        ORDER BY class_key
        """
    ).fetchall()
    return {
        "total_documents": int(total["count"] if total else 0),
        "total_versions": int(versions["count"] if versions else 0),
        "by_class": [{"class_key": row["class_key"], "count": int(row["count"])} for row in by_class_rows],
        "classes": [asdict(class_def) for class_def in CONTENT_CLASS_DEFINITIONS],
    }


def list_content_versions(conn: Any, content_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM content_document_versions
        WHERE content_id = ?
        ORDER BY version_number DESC
        """,
        (content_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_content_document(conn: Any, content_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT d.*, c.title AS class_title, c.description AS class_description, c.root_path AS class_root_path,
               c.glob_pattern AS class_glob_pattern, c.archive_policy AS class_archive_policy
        FROM content_documents d
        LEFT JOIN content_document_classes c ON c.class_key = d.class_key
        WHERE d.content_id = ?
        """,
        (content_id,),
    ).fetchone()
    if not row:
        return None
    payload = _normalize_document_payload(dict(row))
    payload["versions"] = list_content_versions(conn, content_id)
    return payload


def _current_document_text(conn: Any, content_id: str) -> str:
    row = conn.execute(
        """
        SELECT content_markdown
        FROM content_document_versions
        WHERE content_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (content_id,),
    ).fetchone()
    if not row:
        return ""
    return str(row["content_markdown"] or "")


def _version_count(conn: Any, content_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM content_document_versions WHERE content_id = ?",
        (content_id,),
    ).fetchone()
    return int(row["count"] if row else 0)


def save_content_document(
    conn: Any,
    content_id: str,
    content_markdown: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    doc = get_content_document(conn, content_id)
    if doc is None:
        raise ValueError(f"Unknown content_id: {content_id}")
    existing_versions = _version_count(conn, content_id)
    version_number = existing_versions + 1
    version_id = f"{content_id}:v{version_number}"
    next_title = title or _title_from_markdown(Path(doc["file_path"]), content_markdown)
    source_hash = _hash_text(content_markdown)
    now = _now()
    payload = {
        "content_id": content_id,
        "class_key": doc["class_key"],
        "title": next_title,
        "file_path": doc["file_path"],
        "source_sha256": source_hash,
        "source_size_bytes": len(content_markdown.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(doc.get("editable", 1)),
        "versioned": bool(doc.get("versioned", 1)),
        "import_required": bool(doc.get("import_required", 1)),
        "archive_policy": doc.get("archive_policy") or "archive-on-supersede",
    }
    conn.execute(
        """
        INSERT INTO content_document_versions (
            version_id, content_id, version_number, state,
            content_markdown, content_sha256, source_path, source_sha256,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            content_id,
            version_number,
            "published",
            content_markdown,
            source_hash,
            doc["file_path"],
            source_hash,
            actor_id,
            change_summary or "saved via content registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": version_number}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE content_documents
        SET title = ?,
            current_version_id = ?,
            source_sha256 = ?,
            source_size_bytes = ?,
            source_mtime = ?,
            editable = 1,
            archived = 0,
            latest_status = 'current',
            updated_at = ?,
            payload_json = ?
        WHERE content_id = ?
        """,
        (
            next_title,
            version_id,
            source_hash,
            payload["source_size_bytes"],
            now,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
            content_id,
        ),
    )
    return get_content_document(conn, content_id) or payload


def create_content_document(
    conn: Any,
    class_key: str,
    file_path: str,
    content_markdown: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    class_row = conn.execute(
        "SELECT * FROM content_document_classes WHERE class_key = ?",
        (class_key,),
    ).fetchone()
    if class_row is None:
        raise ValueError(f"Unknown content class: {class_key}")
    existing = conn.execute("SELECT 1 FROM content_documents WHERE file_path = ?", (file_path,)).fetchone()
    if existing is not None:
        raise ValueError(f"Content already exists at file_path: {file_path}")
    content_id = f"{class_key}:{file_path}"
    now = _now()
    next_title = title or _title_from_markdown(Path(file_path), content_markdown)
    source_hash = _hash_text(content_markdown)
    payload = {
        "content_id": content_id,
        "class_key": class_key,
        "title": next_title,
        "file_path": file_path,
        "source_sha256": source_hash,
        "source_size_bytes": len(content_markdown.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(class_row["editable"]),
        "versioned": bool(class_row["versioned"]),
        "import_required": bool(class_row["import_required"]),
        "archive_policy": class_row["archive_policy"],
    }
    version_id = f"{content_id}:v1"
    conn.execute(
        """
        INSERT INTO content_document_versions (
            version_id, content_id, version_number, state,
            content_markdown, content_sha256, source_path, source_sha256,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            content_id,
            "published",
            content_markdown,
            source_hash,
            file_path,
            source_hash,
            actor_id,
            change_summary or "created via content registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": 1}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        INSERT INTO content_documents (
            content_id, class_key, file_path, title, current_version_id,
            source_sha256, source_size_bytes, source_mtime, editable,
            archived, latest_status, imported_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'current', ?, ?, ?)
        """,
        (
            content_id,
            class_key,
            file_path,
            next_title,
            version_id,
            source_hash,
            payload["source_size_bytes"],
            now,
            int(payload["editable"]),
            now,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
        ),
    )
    return get_content_document(conn, content_id) or payload


def archive_content_document(
    conn: Any,
    content_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    doc = get_content_document(conn, content_id)
    if doc is None:
        raise ValueError(f"Unknown content_id: {content_id}")
    content_markdown = _current_document_text(conn, content_id)
    if not content_markdown:
        raise ValueError(f"Cannot archive empty content document: {content_id}")
    existing_versions = _version_count(conn, content_id)
    version_number = existing_versions + 1
    version_id = f"{content_id}:v{version_number}"
    now = _now()
    source_hash = _hash_text(content_markdown)
    payload = {
        "content_id": content_id,
        "class_key": doc["class_key"],
        "title": doc["title"],
        "file_path": doc["file_path"],
        "source_sha256": source_hash,
        "source_size_bytes": len(content_markdown.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(doc.get("editable", 1)),
        "versioned": bool(doc.get("versioned", 1)),
        "import_required": bool(doc.get("import_required", 1)),
        "archive_policy": doc.get("archive_policy") or "archive-on-supersede",
    }
    conn.execute(
        """
        INSERT INTO content_document_versions (
            version_id, content_id, version_number, state,
            content_markdown, content_sha256, source_path, source_sha256,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            content_id,
            version_number,
            "archived",
            content_markdown,
            source_hash,
            doc["file_path"],
            source_hash,
            actor_id,
            change_summary or "archived via content registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": version_number, "latest_status": "archived"}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE content_documents
        SET archived = 1,
            latest_status = 'archived',
            current_version_id = ?,
            updated_at = ?,
            payload_json = ?
        WHERE content_id = ?
        """,
        (
            version_id,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "archived"}, sort_keys=True),
            content_id,
        ),
    )
    return get_content_document(conn, content_id) or payload


def restore_content_document(
    conn: Any,
    content_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    doc = get_content_document(conn, content_id)
    if doc is None:
        raise ValueError(f"Unknown content_id: {content_id}")
    content_markdown = _current_document_text(conn, content_id)
    if not content_markdown:
        raise ValueError(f"Cannot restore empty content document: {content_id}")
    existing_versions = _version_count(conn, content_id)
    version_number = existing_versions + 1
    version_id = f"{content_id}:v{version_number}"
    now = _now()
    source_hash = _hash_text(content_markdown)
    payload = {
        "content_id": content_id,
        "class_key": doc["class_key"],
        "title": doc["title"],
        "file_path": doc["file_path"],
        "source_sha256": source_hash,
        "source_size_bytes": len(content_markdown.encode("utf-8")),
        "source_mtime": now,
        "editable": bool(doc.get("editable", 1)),
        "versioned": bool(doc.get("versioned", 1)),
        "import_required": bool(doc.get("import_required", 1)),
        "archive_policy": doc.get("archive_policy") or "archive-on-supersede",
    }
    conn.execute(
        """
        INSERT INTO content_document_versions (
            version_id, content_id, version_number, state,
            content_markdown, content_sha256, source_path, source_sha256,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            content_id,
            version_number,
            "restored",
            content_markdown,
            source_hash,
            doc["file_path"],
            source_hash,
            actor_id,
            change_summary or "restored via content registry",
            now,
            now,
            json.dumps({**payload, "version_id": version_id, "version_number": version_number, "latest_status": "current"}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE content_documents
        SET archived = 0,
            latest_status = 'current',
            current_version_id = ?,
            updated_at = ?,
            payload_json = ?
        WHERE content_id = ?
        """,
        (
            version_id,
            now,
            json.dumps({**payload, "current_version_id": version_id, "latest_status": "current"}, sort_keys=True),
            content_id,
        ),
    )
    return get_content_document(conn, content_id) or payload
