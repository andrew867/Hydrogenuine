from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator, Iterable

from hg_gateway.db import get_connection


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return default


def _normalize_overseer_payload(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return {"_truncated": True}
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "<truncated>":
            return {"_truncated": True}
        return value
    if isinstance(value, dict):
        return {str(key): _normalize_overseer_payload(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_overseer_payload(item, depth + 1) for item in value]
    return value


@contextmanager
def shared_connection() -> Generator[Any, None, None]:
    with get_connection() as conn:
        yield conn


def use_shared_gateway_db(database_path: str | Path) -> bool:
    try:
        from hg_lib.config import get_workspace_root

        root = get_workspace_root().resolve()
    except Exception:
        return False
    path = Path(database_path).expanduser().resolve()
    try:
        path.relative_to(root / "memory")
        return True
    except ValueError:
        return False


def get_operational_state(state_key: str, default: Any = None) -> Any:
    with shared_connection() as conn:
        row = conn.execute(
            "SELECT payload FROM operational_state WHERE state_key = ?",
            (state_key,),
        ).fetchone()
    if row is None:
        return default
    return _json_loads(row[0], default)


def put_operational_state(state_key: str, payload: Any) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO operational_state (state_key, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (state_key, _json_dumps(payload), _iso_now()),
        )


def _snippet(content: str, query: str, radius: int = 96) -> str:
    if not content:
        return ""
    lowered = content.lower()
    needle = (query or "").strip().lower()
    if not needle:
        return content[: radius * 2]
    idx = lowered.find(needle)
    if idx < 0:
        return content[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(content), idx + len(needle) + radius)
    snippet = content[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    return snippet


def check_agent_memory_file_changed(agent_id: str, file_path: str, content: str) -> bool:
    with shared_connection() as conn:
        row = conn.execute(
            "SELECT file_hash FROM memory_agent_documents WHERE agent_id = ? AND file_path = ?",
            (agent_id, file_path),
        ).fetchone()
    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return row is None or str(row[0]) != current_hash


def upsert_agent_memory_document(
    *,
    agent_id: str,
    file_path: str,
    content: str,
    date: str,
    language: str,
    metadata: dict[str, Any],
    word_count: int,
    last_indexed: str,
    file_hash: str,
    source_type: str,
    content_normalized: str,
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_agent_documents (
                agent_id, file_path, content, date, language, metadata, word_count,
                last_indexed, file_hash, source_type, content_normalized
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                file_path,
                content,
                date,
                language,
                _json_dumps(metadata),
                word_count,
                last_indexed,
                file_hash,
                source_type,
                content_normalized,
            ),
        )


def delete_agent_memory_document(agent_id: str, file_path: str) -> None:
    with shared_connection() as conn:
        conn.execute(
            "DELETE FROM memory_agent_documents WHERE agent_id = ? AND file_path = ?",
            (agent_id, file_path),
        )


def get_agent_memory_metadata(agent_id: str, file_path: str) -> dict[str, Any] | None:
    with shared_connection() as conn:
        row = conn.execute(
            """
            SELECT file_path, date, language, word_count, last_indexed, file_hash, source_type, metadata
            FROM memory_agent_documents
            WHERE agent_id = ? AND file_path = ?
            """,
            (agent_id, file_path),
        ).fetchone()
    if row is None:
        return None
    data = {
        "file_path": row[0],
        "date": row[1],
        "language": row[2],
        "word_count": row[3],
        "last_indexed": row[4],
        "file_hash": row[5],
        "source_type": row[6],
    }
    data.update(_json_loads(row[7], {}))
    return data


def list_agent_memory_files(agent_id: str) -> list[str]:
    with shared_connection() as conn:
        rows = conn.execute(
            "SELECT file_path FROM memory_agent_documents WHERE agent_id = ? ORDER BY file_path",
            (agent_id,),
        ).fetchall()
    return [str(row[0]) for row in rows]


def get_agent_memory_documents_by_date_range(agent_id: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
    with shared_connection() as conn:
        rows = conn.execute(
            """
            SELECT file_path, date, language, word_count, source_type
            FROM memory_agent_documents
            WHERE agent_id = ? AND date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (agent_id, start_date, end_date),
        ).fetchall()
    return [
        {
            "file_path": row[0],
            "date": row[1],
            "language": row[2],
            "word_count": row[3],
            "source_type": row[4],
        }
        for row in rows
    ]


def search_agent_memory_documents(
    agent_id: str,
    query: str,
    *,
    limit: int,
    date_start: str | None = None,
    date_end: str | None = None,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT file_path, date, language, content, metadata, source_type
        FROM memory_agent_documents
        WHERE agent_id = ?
    """
    params: list[Any] = [agent_id]
    if date_start:
        sql += " AND date >= ?"
        params.append(date_start)
    if date_end:
        sql += " AND date <= ?"
        params.append(date_end)
    if source_type:
        sql += " AND source_type = ?"
        params.append(source_type)
    if query.strip():
        sql += " AND LOWER(content) LIKE ?"
        params.append(f"%{query.lower()}%")
    sql += " ORDER BY COALESCE(date, '') DESC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "file_path": row[0],
            "date": row[1],
            "language": row[2],
            "snippet": _snippet(str(row[3] or ""), query),
            "rank": 1.0,
            "source_type": row[5],
            "metadata": _json_loads(row[4], {}),
        }
        for row in rows
    ]


def upsert_memory_entity(agent_id: str, entity_type: str, name: str, path: str, summary_excerpt: str | None) -> int:
    now = _iso_now()
    with shared_connection() as conn:
        row = conn.execute(
            "SELECT id FROM memory_entities WHERE agent_id = ? AND type = ? AND name = ?",
            (agent_id, entity_type, name),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE memory_entities
                SET path = ?, summary_excerpt = ?, updated_at = ?
                WHERE id = ?
                """,
                (path, summary_excerpt or "", now, row[0]),
            )
            return int(row[0])
        conn.execute(
            """
            INSERT INTO memory_entities (agent_id, type, name, path, summary_excerpt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (agent_id, entity_type, name, path, summary_excerpt or "", now, now),
        )
        created = conn.execute(
            "SELECT id FROM memory_entities WHERE agent_id = ? AND type = ? AND name = ?",
            (agent_id, entity_type, name),
        ).fetchone()
    return int(created[0]) if created else 0


def upsert_memory_fact(
    *,
    agent_id: str,
    entity_id: int,
    fact: str,
    category: str | None,
    timestamp: str | None,
    source: str | None,
    status: str | None,
    related_entities_json: str | None,
) -> int:
    now = _iso_now()
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT INTO memory_facts (
                agent_id, entity_id, fact, category, timestamp, source, status, related_entities_json, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                entity_id,
                fact,
                category or "",
                timestamp or now,
                source or "",
                status or "active",
                related_entities_json or "[]",
                now,
            ),
        )
        row = conn.execute(
            """
            SELECT id FROM memory_facts
            WHERE agent_id = ? AND entity_id = ? AND fact = ?
            ORDER BY id DESC LIMIT 1
            """,
            (agent_id, entity_id, fact),
        ).fetchone()
    return int(row[0]) if row else 0


def delete_memory_facts_for_entity(agent_id: str, entity_id: int) -> None:
    with shared_connection() as conn:
        conn.execute(
            "DELETE FROM memory_facts WHERE agent_id = ? AND entity_id = ?",
            (agent_id, entity_id),
        )


def search_memory_facts(agent_id: str, query: str, limit: int) -> list[dict[str, Any]]:
    sql = """
        SELECT f.id, f.entity_id, f.fact, f.category, f.timestamp, f.source, e.name
        FROM memory_facts f
        JOIN memory_entities e ON e.id = f.entity_id
        WHERE f.agent_id = ?
    """
    params: list[Any] = [agent_id]
    if query.strip():
        sql += " AND LOWER(f.fact) LIKE ?"
        params.append(f"%{query.lower()}%")
    sql += " ORDER BY COALESCE(f.timestamp, '') DESC, f.id DESC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "id": row[0],
            "entity_id": row[1],
            "fact": row[2],
            "category": row[3],
            "timestamp": row[4],
            "source": row[5],
            "entity_name": row[6],
        }
        for row in rows
    ]


def get_memory_entity_summary(agent_id: str, entity_name: str) -> str | None:
    with shared_connection() as conn:
        row = conn.execute(
            """
            SELECT summary_excerpt
            FROM memory_entities
            WHERE agent_id = ? AND name = ?
            LIMIT 1
            """,
            (agent_id, entity_name),
        ).fetchone()
    return str(row[0]) if row and row[0] else None


def get_recent_memory_entities(agent_id: str, limit: int) -> list[dict[str, Any]]:
    with shared_connection() as conn:
        rows = conn.execute(
            """
            SELECT e.id, e.type, e.name, e.summary_excerpt, e.updated_at
            FROM memory_entities e
            WHERE e.agent_id = ?
            ORDER BY e.updated_at DESC, e.id DESC
            LIMIT ?
            """,
            (agent_id, limit),
        ).fetchall()
    return [
        {
            "id": row[0],
            "type": row[1],
            "name": row[2],
            "summary_excerpt": row[3] or "",
            "updated_at": row[4],
        }
        for row in rows
    ]


def get_entity_graph(agent_id: str, limit_facts: int = 500) -> dict[str, Any]:
    with shared_connection() as conn:
        entity_rows = conn.execute(
            """
            SELECT id, type, name, path, summary_excerpt, created_at, updated_at
            FROM memory_entities
            WHERE agent_id = ?
            ORDER BY id
            """,
            (agent_id,),
        ).fetchall()
        fact_rows = conn.execute(
            """
            SELECT f.id, f.entity_id, f.fact, f.category, f.timestamp, f.source, e.name
            FROM memory_facts f
            JOIN memory_entities e ON e.id = f.entity_id
            WHERE f.agent_id = ?
            ORDER BY f.id
            LIMIT ?
            """,
            (agent_id, limit_facts),
        ).fetchall()
    return {
        "entities": [
            {
                "id": row[0],
                "type": row[1],
                "name": row[2],
                "path": row[3],
                "summary_excerpt": row[4] or "",
                "created_at": row[5],
                "updated_at": row[6],
            }
            for row in entity_rows
        ],
        "facts": [
            {
                "id": row[0],
                "entity_id": row[1],
                "fact": row[2],
                "category": row[3] or "",
                "timestamp": row[4],
                "source": row[5] or "",
                "entity_name": row[6],
            }
            for row in fact_rows
        ],
    }


def upsert_context_entity(
    *,
    entity_id: str,
    entity_type: str,
    agent_id: str | None,
    timestamp: str,
    properties: dict[str, Any],
    content: str,
    language: str,
    content_normalized: str,
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_context_entities (
                entity_id, entity_type, agent_id, timestamp, properties, content,
                language, content_normalized, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM memory_context_entities WHERE entity_id = ?), ?))
            """,
            (
                entity_id,
                entity_type,
                agent_id,
                timestamp,
                _json_dumps(properties),
                content,
                language,
                content_normalized,
                entity_id,
                _iso_now(),
            ),
        )


def upsert_context_relation(
    *,
    relation_id: str,
    from_entity_id: str,
    to_entity_id: str,
    relation_type: str,
    timestamp: str | None,
    properties: dict[str, Any],
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_context_relations (
                relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM memory_context_relations WHERE relation_id = ?), ?))
            """,
            (relation_id, from_entity_id, to_entity_id, relation_type, timestamp, _json_dumps(properties), relation_id, _iso_now()),
        )


def get_context_entity(entity_id: str) -> dict[str, Any] | None:
    with shared_connection() as conn:
        row = conn.execute(
            """
            SELECT entity_id, entity_type, agent_id, timestamp, properties, created_at, content
            FROM memory_context_entities
            WHERE entity_id = ?
            """,
            (entity_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "entity_id": row[0],
        "entity_type": row[1],
        "agent_id": row[2],
        "timestamp": row[3],
        "properties": _json_loads(row[4], {}),
        "created_at": row[5],
        "content": row[6],
    }


def get_related_context_entities(entity_id: str, relation_type: str | None = None, direction: str = "both") -> list[dict[str, Any]]:
    sql = """
        SELECT relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties
        FROM memory_context_relations
        WHERE 1 = 1
    """
    params: list[Any] = []
    if direction == "from":
        sql += " AND from_entity_id = ?"
        params.append(entity_id)
    elif direction == "to":
        sql += " AND to_entity_id = ?"
        params.append(entity_id)
    else:
        sql += " AND (from_entity_id = ? OR to_entity_id = ?)"
        params.extend([entity_id, entity_id])
    if relation_type:
        sql += " AND relation_type = ?"
        params.append(relation_type)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        related_id = row[2] if str(row[1]) == entity_id else row[1]
        entity = get_context_entity(str(related_id))
        if entity:
            entity["relation_type"] = row[3]
            entity["relation_timestamp"] = row[4]
            entity["relation_properties"] = _json_loads(row[5], {})
            results.append(entity)
    return results


def search_context_entities(query: str, *, agent_id: str | None, entity_type: str | None, time_range: tuple[str, str] | None, limit: int) -> list[dict[str, Any]]:
    sql = """
        SELECT entity_id, entity_type, agent_id, timestamp, content, properties
        FROM memory_context_entities
        WHERE 1 = 1
    """
    params: list[Any] = []
    if agent_id:
        sql += " AND agent_id = ?"
        params.append(agent_id)
    if time_range:
        sql += " AND timestamp >= ? AND timestamp <= ?"
        params.extend(time_range)
    if entity_type:
        sql += " AND entity_type = ?"
        params.append(entity_type)
    if query.strip() and query.strip() != "*":
        sql += " AND LOWER(content) LIKE ?"
        params.append(f"%{query.lower()}%")
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "entity_id": row[0],
            "entity_type": row[1],
            "agent_id": row[2],
            "timestamp": row[3],
            "snippet": _snippet(str(row[4] or ""), query),
            "rank": 1.0,
            "properties": _json_loads(row[5], {}),
            "content": row[4],
        }
        for row in rows
    ]


def get_context_decision_chain(topic: str, agent_id: str | None) -> list[dict[str, Any]]:
    return list(reversed(search_context_entities(topic, agent_id=agent_id, entity_type="decision", time_range=None, limit=200)))


def upsert_identity_entity(
    *,
    entity_id: str,
    entity_type: str,
    agent_id: str | None,
    platform: str | None,
    timestamp: str,
    properties: dict[str, Any],
    content: str,
    language: str,
    content_normalized: str,
) -> None:
    now = _iso_now()
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_identity_entities (
                entity_id, entity_type, agent_id, platform, timestamp, properties, content,
                language, content_normalized, created_at, updated_at, deleted_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                COALESCE((SELECT created_at FROM memory_identity_entities WHERE entity_id = ?), ?),
                ?, COALESCE((SELECT deleted_at FROM memory_identity_entities WHERE entity_id = ?), NULL)
            )
            """,
            (
                entity_id,
                entity_type,
                agent_id,
                platform,
                timestamp,
                _json_dumps(properties),
                content,
                language,
                content_normalized,
                entity_id,
                now,
                now,
                entity_id,
            ),
        )


def upsert_identity_relation(
    relation_id: str,
    from_entity_id: str,
    to_entity_id: str,
    relation_type: str,
    timestamp: str | None,
    properties: dict[str, Any],
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_identity_relations (
                relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM memory_identity_relations WHERE relation_id = ?), ?))
            """,
            (relation_id, from_entity_id, to_entity_id, relation_type, timestamp, _json_dumps(properties), relation_id, _iso_now()),
        )


def upsert_identity_version(
    version_id: str,
    persona_file: str,
    content_hash: str,
    platform: str | None,
    persona_set: str | None,
    agent_id: str | None,
    timestamp: str,
    diff_before: str | None,
    diff_after: str | None,
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_identity_versions (
                version_id, persona_file, platform, persona_set, agent_id, timestamp,
                content_hash, diff_before, diff_after, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM memory_identity_versions WHERE version_id = ?), ?))
            """,
            (version_id, persona_file, platform, persona_set, agent_id, timestamp, content_hash, diff_before, diff_after, version_id, _iso_now()),
        )


def upsert_identity_pattern(
    pattern_id: str,
    pattern_type: str,
    agent_id: str | None,
    platform: str | None,
    timestamp: str,
    properties: dict[str, Any],
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_identity_patterns (
                pattern_id, pattern_type, agent_id, platform, timestamp, properties, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM memory_identity_patterns WHERE pattern_id = ?), ?))
            """,
            (pattern_id, pattern_type, agent_id, platform, timestamp, _json_dumps(properties), pattern_id, _iso_now()),
        )


def get_identity_entity(entity_id: str) -> dict[str, Any] | None:
    with shared_connection() as conn:
        row = conn.execute(
            """
            SELECT entity_id, entity_type, agent_id, platform, timestamp, properties, created_at, updated_at, deleted_at, content
            FROM memory_identity_entities
            WHERE entity_id = ?
            """,
            (entity_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "entity_id": row[0],
        "entity_type": row[1],
        "agent_id": row[2],
        "platform": row[3],
        "timestamp": row[4],
        "properties": _json_loads(row[5], {}),
        "created_at": row[6],
        "updated_at": row[7],
        "deleted_at": row[8],
        "content": row[9],
    }


def get_related_identity_entities(entity_id: str, relation_type: str | None = None, direction: str = "both") -> list[dict[str, Any]]:
    sql = """
        SELECT relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties
        FROM memory_identity_relations
        WHERE 1 = 1
    """
    params: list[Any] = []
    if direction == "from":
        sql += " AND from_entity_id = ?"
        params.append(entity_id)
    elif direction == "to":
        sql += " AND to_entity_id = ?"
        params.append(entity_id)
    else:
        sql += " AND (from_entity_id = ? OR to_entity_id = ?)"
        params.extend([entity_id, entity_id])
    if relation_type:
        sql += " AND relation_type = ?"
        params.append(relation_type)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        related_id = row[2] if str(row[1]) == entity_id else row[1]
        entity = get_identity_entity(str(related_id))
        if entity:
            entity["relation_type"] = row[3]
            entity["relation_timestamp"] = row[4]
            entity["relation_properties"] = _json_loads(row[5], {})
            results.append(entity)
    return results


def search_identity_entities(query: str, *, agent_id: str | None, entity_type: str | None, platform: str | None, limit: int) -> list[dict[str, Any]]:
    sql = """
        SELECT entity_id, entity_type, agent_id, platform, timestamp, properties, content
        FROM memory_identity_entities
        WHERE deleted_at IS NULL
    """
    params: list[Any] = []
    if agent_id:
        sql += " AND agent_id = ?"
        params.append(agent_id)
    if entity_type:
        sql += " AND entity_type = ?"
        params.append(entity_type)
    if platform:
        sql += " AND platform = ?"
        params.append(platform)
    if query.strip():
        sql += " AND LOWER(content) LIKE ?"
        params.append(f"%{query.lower()}%")
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "entity_id": row[0],
            "entity_type": row[1],
            "agent_id": row[2],
            "platform": row[3],
            "timestamp": row[4],
            "properties": _json_loads(row[5], {}),
            "content": row[6],
            "snippet": _snippet(str(row[6] or ""), query),
            "rank": 1.0,
        }
        for row in rows
    ]


def get_identity_versions(persona_file: str, agent_id: str | None, limit: int) -> list[dict[str, Any]]:
    sql = """
        SELECT version_id, persona_file, content_hash, platform, persona_set, agent_id, timestamp, diff_before, diff_after
        FROM memory_identity_versions
        WHERE persona_file = ?
    """
    params: list[Any] = [persona_file]
    if agent_id:
        sql += " AND agent_id = ?"
        params.append(agent_id)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "version_id": row[0],
            "persona_file": row[1],
            "content_hash": row[2],
            "platform": row[3],
            "persona_set": row[4],
            "agent_id": row[5],
            "timestamp": row[6],
            "diff_before": row[7],
            "diff_after": row[8],
        }
        for row in rows
    ]


def upsert_latest_overseer_state(payload: dict[str, Any]) -> None:
    normalized = _normalize_overseer_payload(dict(payload or {}))
    stamped = str(normalized.get("timestamp") or _iso_now())
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO overseer_latest_state (slot, payload, updated_at)
            VALUES ('latest', ?, ?)
            """,
            (_json_dumps(normalized), stamped),
        )


def append_overseer_timeseries(payload: dict[str, Any]) -> str:
    normalized = _normalize_overseer_payload(dict(payload or {}))
    event_id = str(normalized.get("event_id") or uuid.uuid4())
    timestamp = str(normalized.get("timestamp") or _iso_now())
    with shared_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO overseer_timeseries (event_id, timestamp, payload) VALUES (?, ?, ?)",
            (event_id, timestamp, _json_dumps(normalized)),
        )
    return event_id


def list_overseer_timeseries(*, hours: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
    sql = "SELECT payload FROM overseer_timeseries"
    params: list[Any] = []
    if hours is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        sql += " WHERE timestamp >= ?"
        params.append(cutoff_iso)
    sql += " ORDER BY timestamp ASC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_json_loads(row[0], {}) for row in rows]


def get_latest_overseer_state() -> dict[str, Any] | None:
    with shared_connection() as conn:
        row = conn.execute(
            "SELECT payload FROM overseer_latest_state WHERE slot = 'latest'"
        ).fetchone()
    return _json_loads(row[0], None) if row else None


def append_meditation_report(payload: dict[str, Any]) -> str:
    raw = _json_dumps(payload)
    report_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO meditation_reports (report_id, actor_id, window_end_ts, created_at, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                report_id,
                payload.get("actor_id"),
                payload.get("window_end_ts"),
                str(payload.get("created_at") or _iso_now()),
                raw,
            ),
        )
    return report_id


def list_meditation_reports(limit: int = 200) -> list[dict[str, Any]]:
    with shared_connection() as conn:
        rows = conn.execute(
            "SELECT payload FROM meditation_reports ORDER BY COALESCE(window_end_ts, created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_json_loads(row[0], {}) for row in rows]


def append_audit_entry(role: str, action: str, resource_id: str, details: dict[str, Any] | None) -> str:
    entry_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).timestamp()
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_entries (entry_id, role, action, resource_id, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entry_id, role, action, resource_id, timestamp, _json_dumps(details or {})),
        )
    return entry_id


def append_approval_override(approval_id: str, decision: str, role: str | None, timestamp: str) -> str:
    override_id = str(uuid.uuid4())
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT INTO approval_overrides (override_id, approval_id, decision, role, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (override_id, approval_id, decision, role, timestamp),
        )
    return override_id


def append_steering_telemetry(event_name: str, payload: dict[str, Any]) -> str:
    event_id = str(uuid.uuid4())
    timestamp = str(payload.get("timestamp") or _iso_now())
    body = dict(payload)
    body.setdefault("timestamp", timestamp)
    with shared_connection() as conn:
        conn.execute(
            "INSERT INTO steering_telemetry (event_id, timestamp, event_name, payload) VALUES (?, ?, ?, ?)",
            (event_id, timestamp, event_name, _json_dumps(body)),
        )
    return event_id


def list_steering_telemetry(limit: int = 100) -> list[dict[str, Any]]:
    with shared_connection() as conn:
        rows = conn.execute(
            "SELECT event_name, payload FROM steering_telemetry ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = _json_loads(row[1], {})
        if "event" not in payload:
            payload["event"] = row[0]
        events.append(payload)
    return events


def append_agent_decision(
    *,
    decision_id: str,
    agent_id: str,
    timestamp: str,
    action: str,
    rationale: str,
    alternatives: Iterable[str],
    tradeoffs: str | None,
    context: str | None,
    outcome: str | None,
) -> None:
    with shared_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_decisions (
                decision_id, agent_id, timestamp, action, rationale, alternatives, tradeoffs, context, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                agent_id,
                timestamp,
                action,
                rationale,
                _json_dumps(list(alternatives)),
                tradeoffs,
                context,
                outcome,
            ),
        )


def list_agent_decisions(agent_id: str, *, days: int | None = None, search_query: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    sql = """
        SELECT decision_id, timestamp, action, rationale, alternatives, tradeoffs, context, outcome
        FROM agent_decisions
        WHERE agent_id = ?
    """
    params: list[Any] = [agent_id]
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        sql += " AND timestamp >= ?"
        params.append(cutoff.isoformat().replace("+00:00", "Z"))
    if search_query:
        like = f"%{search_query.lower()}%"
        sql += " AND (LOWER(action) LIKE ? OR LOWER(rationale) LIKE ? OR LOWER(COALESCE(context, '')) LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with shared_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "decision_id": row[0],
            "timestamp": row[1],
            "action": row[2],
            "rationale": row[3],
            "alternatives": _json_loads(row[4], []),
            "tradeoffs": row[5],
            "context": row[6],
            "outcome": row[7],
        }
        for row in rows
    ]
