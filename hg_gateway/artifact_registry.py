from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


ARTIFACT_CLASS_ORDER = ("archive_snapshot", "backup", "screenshot", "artifact", "reflection", "snapshot", "log")
ARTIFACT_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".log", ".yaml", ".yml", ".xml", ".csv"}
ARTIFACT_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
ARTIFACT_BACKUP_SUFFIXES = {".dump", ".sql", ".sqlite3", ".tar", ".zip", ".bak", ".backup"}
ARTIFACT_ROOTS = (
    Path("memory") / "overseer",
    Path("memory") / "artifacts",
    Path("memory") / "archive",
    Path("memory") / "tenants",
    Path("artifacts"),
    Path("backups"),
    Path("docs") / "proofs" / "out",
    Path("docs") / "ux" / "screenshots",
    Path("operator_console") / "ui" / "playwright-screenshots",
    Path("client_ui") / "playwright-screenshots",
)


@dataclass(frozen=True)
class ArtifactClassDefinition:
    class_key: str
    title: str
    root_path: str
    glob_pattern: str
    description: str
    editable: bool = False
    versioned: bool = True
    import_required: bool = True
    archive_policy: str = "retain-and-index"
    metadata_json: str = "{}"


@dataclass(frozen=True)
class ArtifactInventoryItem:
    artifact_id: str
    class_key: str
    title: str
    file_path: str
    source_sha256: str
    source_size_bytes: int
    source_mtime: str
    content_kind: str
    mime_type: str
    line_count: int
    word_count: int
    editable: bool = False
    versioned: bool = True
    import_required: bool = True
    archive_policy: str = "retain-and-index"
    payload_json: str = "{}"


ARTIFACT_CLASS_DEFINITIONS: tuple[ArtifactClassDefinition, ...] = (
    ArtifactClassDefinition(
        class_key="archive_snapshot",
        title="Archive snapshots",
        root_path="memory/archive",
        glob_pattern="**/*",
        description="Recovered archive snapshots and archived workspace state.",
        metadata_json='{"source_roots":["memory/archive"]}',
    ),
    ArtifactClassDefinition(
        class_key="backup",
        title="Backups",
        root_path="backups",
        glob_pattern="**/*",
        description="Workspace and gateway backups plus backup manifests.",
        metadata_json='{"source_roots":["backups","artifacts/backups","memory/backups"]}',
    ),
    ArtifactClassDefinition(
        class_key="screenshot",
        title="Screenshots",
        root_path="docs/ux/screenshots",
        glob_pattern="**/*",
        description="Playwright and browser screenshots captured during validation.",
        metadata_json='{"source_roots":["docs/ux/screenshots","operator_console/ui/playwright-screenshots","client_ui/playwright-screenshots"]}',
    ),
    ArtifactClassDefinition(
        class_key="artifact",
        title="Generated artifacts",
        root_path="memory/artifacts",
        glob_pattern="**/*",
        description="Generated proof bundles, exports, and structured output artifacts.",
        metadata_json='{"source_roots":["memory/artifacts","docs/proofs/out"]}',
    ),
    ArtifactClassDefinition(
        class_key="reflection",
        title="Reflection artifacts",
        root_path="memory/reflections",
        glob_pattern="**/*",
        description="Typed reflection outputs with source links, review state, and confidence.",
        editable=False,
        versioned=True,
        import_required=False,
        archive_policy="retain-and-review",
        metadata_json='{"source_roots":["memory/reflections"],"typed":"yes","promotable":"yes"}',
    ),
    ArtifactClassDefinition(
        class_key="snapshot",
        title="Snapshots",
        root_path="memory/tenants",
        glob_pattern="**/*",
        description="Recoverable run snapshots, exports, and replayable workspace state.",
        metadata_json='{"source_roots":["memory/tenants","docs/proofs/out"]}',
    ),
    ArtifactClassDefinition(
        class_key="log",
        title="Logs",
        root_path="memory/overseer",
        glob_pattern="**/*",
        description="Operational logs, JSONL traces, and durable text event streams.",
        metadata_json='{"source_roots":["memory/overseer"]}',
    ),
)


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_rel_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _title_from_path(path: Path, content: str | None = None) -> str:
    if content:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip() or path.stem
    if path.name == "last_backup.json":
        return "Last backup marker"
    if path.name == "last_manifest.json":
        return "Last backup manifest"
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.stem


def _is_archive_snapshot_path(rel: Path) -> bool:
    if "archive" not in rel.parts:
        return False
    if rel.parts[:2] == (".cursor", "plans"):
        return False
    return True


def _is_backup_path(rel: Path) -> bool:
    name = rel.name.lower()
    if "backups" in rel.parts:
        return True
    if name in {"last_backup.json", "last_manifest.json"}:
        return True
    return rel.suffix.lower() in ARTIFACT_BACKUP_SUFFIXES


def _is_screenshot_path(rel: Path) -> bool:
    if any(part.lower() in {"screenshot", "screenshots"} for part in rel.parts):
        return True
    return rel.suffix.lower() in ARTIFACT_IMAGE_SUFFIXES


def _is_snapshot_path(rel: Path) -> bool:
    return rel.parts[:3] == ("docs", "proofs", "out") or "dag_runs" in rel.parts or "tenants" in rel.parts


def _is_log_path(rel: Path) -> bool:
    if rel.suffix.lower() in {".jsonl", ".log"}:
        return True
    if rel.suffix.lower() in ARTIFACT_TEXT_SUFFIXES and any(part.lower() in {"memory", "automation", "overseer", "logs", "log", "audit"} for part in rel.parts):
        return True
    return False


def _is_artifact_path(rel: Path) -> bool:
    if rel.parts[:2] == ("memory", "artifacts"):
        return True
    if rel.parts[:3] == ("docs", "proofs", "out"):
        return True
    return False


def classify_artifact_path(rel_path: str) -> str | None:
    rel = Path(rel_path)
    if _is_archive_snapshot_path(rel):
        return "archive_snapshot"
    if _is_backup_path(rel):
        return "backup"
    if _is_screenshot_path(rel):
        return "screenshot"
    if _is_artifact_path(rel):
        return "artifact"
    if _is_snapshot_path(rel):
        return "snapshot"
    if _is_log_path(rel):
        return "log"
    return None


def discover_artifact_files(root: Path | None = None) -> list[Path]:
    workspace = root or workspace_root()
    candidates: list[Path] = []
    for rel in ARTIFACT_ROOTS:
        base = workspace / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel_path = path.relative_to(workspace)
            if classify_artifact_path(rel_path.as_posix()) is None:
                continue
            candidates.append(path)
    return sorted({path.resolve() for path in candidates}, key=lambda p: p.as_posix().lower())


def _inventory_item(path: Path, workspace: Path) -> ArtifactInventoryItem | None:
    rel_path = _normalize_rel_path(path, workspace)
    class_key = classify_artifact_path(rel_path)
    if class_key is None:
        return None
    try:
        content_bytes = path.read_bytes()
    except Exception:
        return None
    content = _read_text(path)
    title = _title_from_path(path, content)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    stat = path.stat()
    payload = {
        "class_key": class_key,
        "file_path": rel_path,
        "title": title,
        "mime_type": mime_type,
        "source_roots": [rel.as_posix() for rel in ARTIFACT_ROOTS if str(path).startswith(str(workspace / rel))],
        "kind_reason": class_key,
        "text": bool(content is not None),
    }
    return ArtifactInventoryItem(
        artifact_id=f"{class_key}:{rel_path}",
        class_key=class_key,
        title=title,
        file_path=rel_path,
        source_sha256=_hash_bytes(content_bytes),
        source_size_bytes=stat.st_size,
        source_mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        content_kind=class_key,
        mime_type=mime_type,
        line_count=(content.count("\n") + (1 if content else 0)) if content is not None else 0,
        word_count=len(content.split()) if content is not None else 0,
        payload_json=json.dumps(payload, sort_keys=True),
    )


def inventory_artifacts(root: Path | None = None) -> list[ArtifactInventoryItem]:
    workspace = root or workspace_root()
    items: list[ArtifactInventoryItem] = []
    for path in discover_artifact_files(workspace):
        item = _inventory_item(path, workspace)
        if item is not None:
            items.append(item)
    return items


def ensure_artifact_registry_seed(conn: Any) -> None:
    for class_def in ARTIFACT_CLASS_DEFINITIONS:
        conn.execute(
            """
            INSERT INTO artifact_registry_classes (
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


def _artifact_entry_payload(item: ArtifactInventoryItem) -> dict[str, Any]:
    return {
        "artifact_id": item.artifact_id,
        "class_key": item.class_key,
        "title": item.title,
        "file_path": item.file_path,
        "source_sha256": item.source_sha256,
        "source_size_bytes": item.source_size_bytes,
        "source_mtime": item.source_mtime,
        "content_kind": item.content_kind,
        "mime_type": item.mime_type,
        "line_count": item.line_count,
        "word_count": item.word_count,
        "editable": item.editable,
        "versioned": item.versioned,
        "import_required": item.import_required,
        "archive_policy": item.archive_policy,
    }


def _artifact_version_payload(item: ArtifactInventoryItem, version_number: int, state: str) -> dict[str, Any]:
    payload = _artifact_entry_payload(item)
    payload.update({"version_number": version_number, "state": state})
    return payload


def _reflection_payload(
    *,
    artifact_id: str,
    title: str,
    summary: str,
    findings_json: Any,
    source_event_ids: list[str],
    source_memory_ids: list[str],
    source_links: list[dict[str, Any]],
    confidence: float,
    verification_status: str,
    reviewed_by: str | None,
    promoted_at: str | None,
    created_at: str,
    updated_at: str,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "class_key": "reflection",
        "title": title,
        "summary": summary,
        "findings_json": findings_json,
        "source_event_ids": source_event_ids,
        "source_memory_ids": source_memory_ids,
        "source_links": source_links,
        "confidence": confidence,
        "verification_status": verification_status,
        "reviewed_by": reviewed_by,
        "promoted_at": promoted_at,
        "created_at": created_at,
        "updated_at": updated_at,
        "source_type": "reflection",
        "review_state": verification_status,
    }


def _existing_latest_version(conn: Any, artifact_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT version_id, version_number, source_sha256
        FROM artifact_registry_versions
        WHERE artifact_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (artifact_id,),
    ).fetchone()
    return dict(row) if row else None


def _fetch_artifact_entry(conn: Any, artifact_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM artifact_registry_entries WHERE artifact_id = ?", (artifact_id,)).fetchone()
    return dict(row) if row else None


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def sync_artifact_registry(conn: Any, items: Iterable[ArtifactInventoryItem] | None = None, root: Path | None = None) -> dict[str, Any]:
    inventory = list(items or inventory_artifacts(root))
    ensure_artifact_registry_seed(conn)
    created = 0
    updated = 0
    unchanged = 0
    versions = 0
    for item in inventory:
        payload = _artifact_entry_payload(item)
        existing = _fetch_artifact_entry(conn, item.artifact_id)
        now = _now()
        if existing is None:
            version_id = f"artifact-version:{item.artifact_id}:1"
            conn.execute(
                """
                INSERT INTO artifact_registry_entries (
                    artifact_id, class_key, file_path, title, source_sha256,
                    source_size_bytes, source_mtime, content_kind, mime_type,
                    current_version_id, latest_status, active, imported_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    item.artifact_id,
                    item.class_key,
                    item.file_path,
                    item.title,
                    item.source_sha256,
                    item.source_size_bytes,
                    item.source_mtime,
                    item.content_kind,
                    item.mime_type,
                    version_id,
                    "current",
                    now,
                    now,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            conn.execute(
                """
                INSERT INTO artifact_registry_versions (
                    version_id, artifact_id, version_number, state, file_path, class_key,
                    content_kind, mime_type, source_sha256, source_size_bytes, source_mtime,
                    author_id, change_summary, created_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    item.artifact_id,
                    1,
                    "imported",
                    item.file_path,
                    item.class_key,
                    item.content_kind,
                    item.mime_type,
                    item.source_sha256,
                    item.source_size_bytes,
                    item.source_mtime,
                    None,
                    "imported via artifact registry",
                    now,
                    now,
                    json.dumps(_artifact_version_payload(item, 1, "imported"), sort_keys=True),
                ),
            )
            created += 1
            versions += 1
            conn.commit()
            continue
        if str(existing.get("source_sha256") or "") == item.source_sha256 and int(existing.get("source_size_bytes") or 0) == item.source_size_bytes:
            conn.execute(
                """
                UPDATE artifact_registry_entries
                   SET updated_at = ?, payload_json = ?
                 WHERE artifact_id = ?
                """,
                (now, json.dumps(payload, sort_keys=True), item.artifact_id),
            )
            unchanged += 1
            conn.commit()
            continue
        latest = _existing_latest_version(conn, item.artifact_id)
        next_version = int((latest or {}).get("version_number") or 0) + 1
        version_id = f"artifact-version:{item.artifact_id}:{next_version}"
        conn.execute(
            """
            INSERT INTO artifact_registry_versions (
                version_id, artifact_id, version_number, state, file_path, class_key,
                content_kind, mime_type, source_sha256, source_size_bytes, source_mtime,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                item.artifact_id,
                next_version,
                "updated",
                item.file_path,
                item.class_key,
                item.content_kind,
                item.mime_type,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                None,
                "updated via artifact registry sync",
                now,
                now,
                json.dumps(_artifact_version_payload(item, next_version, "updated"), sort_keys=True),
            ),
        )
        conn.execute(
            """
            UPDATE artifact_registry_entries
               SET class_key = ?,
                   file_path = ?,
                   title = ?,
                   source_sha256 = ?,
                   source_size_bytes = ?,
                   source_mtime = ?,
                   content_kind = ?,
                   mime_type = ?,
                   current_version_id = ?,
                   latest_status = 'current',
                   active = 1,
                   updated_at = ?,
                   payload_json = ?
             WHERE artifact_id = ?
            """,
            (
                item.class_key,
                item.file_path,
                item.title,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                item.content_kind,
                item.mime_type,
                version_id,
                now,
                json.dumps(payload, sort_keys=True),
                item.artifact_id,
            ),
        )
        updated += 1
        versions += 1
        conn.commit()
    return {
        "classes": len(ARTIFACT_CLASS_DEFINITIONS),
        "artifacts": len(inventory),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "versions": versions,
    }


def upsert_artifact_record(
    conn: Any,
    *,
    file_path: str,
    class_key: str,
    title: str | None = None,
    content_kind: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    workspace = root or workspace_root()
    path = workspace / file_path
    if not path.exists():
        raise FileNotFoundError(f"Artifact path not found: {path}")
    item = _inventory_item(path, workspace)
    if item is None:
        item = ArtifactInventoryItem(
            artifact_id=f"{class_key}:{file_path}",
            class_key=class_key,
            title=title or _title_from_path(path, None),
            file_path=file_path,
            source_sha256=_hash_file(path),
            source_size_bytes=path.stat().st_size,
            source_mtime=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            content_kind=content_kind or class_key,
            mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            line_count=0,
            word_count=0,
            payload_json=json.dumps({"file_path": file_path, "class_key": class_key, "content_kind": content_kind or class_key}, sort_keys=True),
        )
    if title:
        item = ArtifactInventoryItem(
            **{**asdict(item), "title": title, "payload_json": item.payload_json}
        )
    ensure_artifact_registry_seed(conn)
    now = _now()
    payload = _artifact_entry_payload(item)
    existing = _fetch_artifact_entry(conn, item.artifact_id)
    if existing is None:
        version_id = f"artifact-version:{item.artifact_id}:1"
        conn.execute(
            """
            INSERT INTO artifact_registry_entries (
                artifact_id, class_key, file_path, title, source_sha256,
                source_size_bytes, source_mtime, content_kind, mime_type,
                current_version_id, latest_status, active, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                item.artifact_id,
                item.class_key,
                item.file_path,
                item.title,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                item.content_kind,
                item.mime_type,
                version_id,
                "current",
                now,
                now,
                json.dumps(payload, sort_keys=True),
            ),
        )
        conn.execute(
            """
            INSERT INTO artifact_registry_versions (
                version_id, artifact_id, version_number, state, file_path, class_key,
                content_kind, mime_type, source_sha256, source_size_bytes, source_mtime,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                item.artifact_id,
                1,
                "imported",
                item.file_path,
                item.class_key,
                item.content_kind,
                item.mime_type,
                item.source_sha256,
                item.source_size_bytes,
                item.source_mtime,
                actor_id,
                change_summary or "imported artifact record",
                now,
                now,
                json.dumps({**_artifact_version_payload(item, 1, "imported"), "actor_id": actor_id, "change_summary": change_summary}, sort_keys=True),
            ),
        )
        return get_artifact_registry_entry(conn, item.artifact_id) or {}
    latest = _existing_latest_version(conn, item.artifact_id)
    next_version = int((latest or {}).get("version_number") or 0) + 1
    version_id = f"artifact-version:{item.artifact_id}:{next_version}"
    conn.execute(
        """
        INSERT INTO artifact_registry_versions (
            version_id, artifact_id, version_number, state, file_path, class_key,
            content_kind, mime_type, source_sha256, source_size_bytes, source_mtime,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            item.artifact_id,
            next_version,
            "updated",
            item.file_path,
            item.class_key,
            item.content_kind,
            item.mime_type,
            item.source_sha256,
            item.source_size_bytes,
            item.source_mtime,
            actor_id,
            change_summary or "updated artifact record",
            now,
            now,
            json.dumps({**_artifact_version_payload(item, next_version, "updated"), "actor_id": actor_id, "change_summary": change_summary}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        UPDATE artifact_registry_entries
           SET class_key = ?,
               file_path = ?,
               title = ?,
               source_sha256 = ?,
               source_size_bytes = ?,
               source_mtime = ?,
               content_kind = ?,
               mime_type = ?,
               current_version_id = ?,
               latest_status = 'current',
               active = 1,
               updated_at = ?,
               payload_json = ?
         WHERE artifact_id = ?
        """,
        (
            item.class_key,
            item.file_path,
            item.title,
            item.source_sha256,
            item.source_size_bytes,
            item.source_mtime,
            item.content_kind,
            item.mime_type,
            version_id,
            now,
            json.dumps(payload, sort_keys=True),
            item.artifact_id,
        ),
    )
    return get_artifact_registry_entry(conn, item.artifact_id) or {}


def upsert_reflection_artifact(
    conn: Any,
    *,
    artifact_id: str,
    title: str,
    summary: str,
    findings_json: Any,
    source_event_ids: list[str] | None = None,
    source_memory_ids: list[str] | None = None,
    source_links: list[dict[str, Any]] | None = None,
    confidence: float = 0.0,
    verification_status: str = "provisional",
    reviewed_by: str | None = None,
    promoted_at: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    ensure_artifact_registry_seed(conn)
    now = _now()
    source_event_ids = [str(item).strip() for item in (source_event_ids or []) if str(item).strip()]
    source_memory_ids = [str(item).strip() for item in (source_memory_ids or []) if str(item).strip()]
    source_links = [dict(item) for item in (source_links or []) if isinstance(item, dict)]
    payload = _reflection_payload(
        artifact_id=artifact_id,
        title=title,
        summary=summary,
        findings_json=findings_json,
        source_event_ids=source_event_ids,
        source_memory_ids=source_memory_ids,
        source_links=source_links,
        confidence=float(confidence),
        verification_status=verification_status,
        reviewed_by=reviewed_by,
        promoted_at=promoted_at,
        created_at=now,
        updated_at=now,
    )
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    content_sha = _hash_bytes(payload_json.encode("utf-8"))
    file_path = f"memory/reflections/{artifact_id}.json"
    existing = _fetch_artifact_entry(conn, artifact_id)
    if existing is None:
        version_id = f"artifact-version:{artifact_id}:1"
        conn.execute(
            """
            INSERT INTO artifact_registry_entries (
                artifact_id, class_key, file_path, title, source_sha256,
                source_size_bytes, source_mtime, content_kind, mime_type,
                current_version_id, latest_status, active, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                artifact_id,
                "reflection",
                file_path,
                title,
                content_sha,
                len(payload_json.encode("utf-8")),
                now,
                "reflection",
                "application/json",
                version_id,
                verification_status,
                now,
                now,
                payload_json,
            ),
        )
        conn.execute(
            """
            INSERT INTO artifact_registry_versions (
                version_id, artifact_id, version_number, state, file_path, class_key,
                content_kind, mime_type, source_sha256, source_size_bytes, source_mtime,
                author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                artifact_id,
                1,
                verification_status,
                file_path,
                "reflection",
                "reflection",
                "application/json",
                content_sha,
                len(payload_json.encode("utf-8")),
                now,
                actor_id,
                change_summary or "created reflection artifact",
                now,
                now,
                json.dumps({**payload, "actor_id": actor_id, "change_summary": change_summary}, sort_keys=True, ensure_ascii=False),
            ),
        )
        return get_artifact_registry_entry(conn, artifact_id) or {}
    latest = _existing_latest_version(conn, artifact_id)
    next_version = int((latest or {}).get("version_number") or 0) + 1
    version_id = f"artifact-version:{artifact_id}:{next_version}"
    conn.execute(
        """
        INSERT INTO artifact_registry_versions (
            version_id, artifact_id, version_number, state, file_path, class_key,
            content_kind, mime_type, source_sha256, source_size_bytes, source_mtime,
            author_id, change_summary, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            artifact_id,
            next_version,
            verification_status,
            file_path,
            "reflection",
            "reflection",
            "application/json",
            content_sha,
            len(payload_json.encode("utf-8")),
            now,
            actor_id,
            change_summary or "updated reflection artifact",
            now,
            now,
            json.dumps({**payload, "actor_id": actor_id, "change_summary": change_summary, "version_number": next_version}, sort_keys=True, ensure_ascii=False),
        ),
    )
    conn.execute(
        """
        UPDATE artifact_registry_entries
           SET title = ?,
               source_sha256 = ?,
               source_size_bytes = ?,
               source_mtime = ?,
               content_kind = 'reflection',
               mime_type = 'application/json',
               current_version_id = ?,
               latest_status = ?,
               active = 1,
               updated_at = ?,
               payload_json = ?
         WHERE artifact_id = ?
        """,
        (
            title,
            content_sha,
            len(payload_json.encode("utf-8")),
            now,
            version_id,
            verification_status,
            now,
            payload_json,
            artifact_id,
        ),
    )
    return get_artifact_registry_entry(conn, artifact_id) or {}


def list_artifact_inventory(conn: Any, class_key: str | None = None) -> list[dict[str, Any]]:
    if class_key:
        rows = conn.execute(
            """
            SELECT *
            FROM artifact_registry_entries
            WHERE class_key = ?
            ORDER BY updated_at DESC, file_path ASC
            """,
            (class_key,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT *
            FROM artifact_registry_entries
            ORDER BY updated_at DESC, file_path ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_artifact_versions(conn: Any, artifact_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM artifact_registry_versions
        WHERE artifact_id = ?
        ORDER BY version_number DESC
        """,
        (artifact_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_artifact_registry_entry(conn: Any, artifact_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM artifact_registry_entries WHERE artifact_id = ?", (artifact_id,)).fetchone()
    if row is None:
        return None
    entry = dict(row)
    entry["versions"] = list_artifact_versions(conn, artifact_id)
    return entry


def get_artifact_inventory_summary(conn: Any) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS count FROM artifact_registry_entries").fetchone()
    versions = conn.execute("SELECT COUNT(*) AS count FROM artifact_registry_versions").fetchone()
    by_class = conn.execute(
        """
        SELECT class_key, COUNT(*) AS count
        FROM artifact_registry_entries
        GROUP BY class_key
        ORDER BY class_key
        """
    ).fetchall()
    return {
        "total_artifacts": int(total["count"] if total else 0),
        "total_versions": int(versions["count"] if versions else 0),
        "by_class": [dict(row) for row in by_class],
    }
