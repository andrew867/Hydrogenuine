"""
Idempotent demo seed: ensure default tenant has at least one principal.
Used when starting the demo stack so the DB is pre-filled (production code path, pre-filled data).
Run: python -m hg_gateway.seed_demo
Uses HG_GATEWAY_DB_PATH (same as gateway); safe to run multiple times.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from hg_gateway.db import get_connection
from hg_core.temporal_changelog import record_major_disruption_once

IMPORT_MARKER_TABLE = "demo_bootstrap_imports"
LEGACY_SQLITE_MARKER = "legacy_sqlite_gateway"
LEGACY_FILE_MARKER = "legacy_file_runtime"
LEGACY_RUNS_MARKER = "legacy_run_index"
LEGACY_MEMORY_MARKER = "legacy_memory_backfill"
LEGACY_SOCIAL_STATE_MARKER = "legacy_social_state"
DEMO_IMPORT_TABLES = {
    "principals",
    "tenant_settings",
    "tenant_retention",
    "tenant_usage",
    "chats",
    "messages",
    "agents",
    "documents",
    "document_pages",
    "document_chunks",
    "document_jobs",
    "approvals",
    "approval_requests",
    "approval_chat_lock",
    "browser_sessions",
    "events",
    "event_stream",
    "proof_artifacts",
    "social_accounts",
    "social_actions",
    "stepup_challenges",
    "stepup_secrets",
    "tool_effect_ledger",
    "turn_provenance",
}

DEMO_SOCIAL_APPROVAL_RULES = [
    {
        "id": "demo-fourclaw-posts",
        "label": "Auto approve Fourclaw posts",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["fourclaw-auto-post", "fourclaw-auto-post-cadence"],
        "platforms": ["fourclaw"],
        "modes": ["post"],
    },
    {
        "id": "demo-fourclaw-replies",
        "label": "Auto approve Fourclaw replies",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["fourclaw-engage"],
        "platforms": ["fourclaw"],
        "modes": ["reply"],
    },
    {
        "id": "demo-moltbook-posts",
        "label": "Auto approve Moltbook posts",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["moltbook-auto-post"],
        "platforms": ["moltbook"],
        "modes": ["post"],
    },
    {
        "id": "demo-moltbook-replies",
        "label": "Auto approve Moltbook replies",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["moltbook-engage"],
        "platforms": ["moltbook"],
        "modes": ["reply"],
    },
    {
        "id": "demo-aichan-posts",
        "label": "Auto approve Aichan posts",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["aichan-auto-post", "aichan-post"],
        "platforms": ["aichan"],
        "modes": ["post"],
    },
    {
        "id": "demo-aichan-replies",
        "label": "Auto approve Aichan replies",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["aichan-engage"],
        "platforms": ["aichan"],
        "modes": ["reply"],
    },
    {
        "id": "demo-agentchan-posts",
        "label": "Auto approve Agentchan posts",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["agentchan-auto-post"],
        "platforms": ["agentchan"],
        "modes": ["post"],
    },
    {
        "id": "demo-agentchan-replies",
        "label": "Auto approve Agentchan replies",
        "enabled": True,
        "decision": "auto_approve",
        "kinds": ["social_write"],
        "risks": ["high"],
        "workflow_ids": ["agentchan-engage"],
        "platforms": ["agentchan"],
        "modes": ["reply"],
    },
]


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _quote_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _ensure_import_marker_table(conn) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {IMPORT_MARKER_TABLE} (
            import_name TEXT PRIMARY KEY,
            imported_at TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    conn.commit()


def _has_import_marker(conn, import_name: str) -> bool:
    row = conn.execute(
        f"SELECT import_name FROM {IMPORT_MARKER_TABLE} WHERE import_name = ?",
        (import_name,),
    ).fetchone()
    return row is not None


def _write_import_marker(conn, import_name: str, metadata: dict) -> None:
    conn.execute(
        f"""
        INSERT INTO {IMPORT_MARKER_TABLE} (import_name, imported_at, metadata)
        VALUES (?, CURRENT_TIMESTAMP, ?)
        ON CONFLICT (import_name) DO UPDATE
        SET imported_at = CURRENT_TIMESTAMP, metadata = EXCLUDED.metadata
        """,
        (import_name, json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
    )


def _target_has_demo_rows(conn) -> bool:
    for table in ("chats", "messages", "runs", "principals"):
        try:
            row = conn.execute(f"SELECT COUNT(*) AS count FROM {_quote_ident(table)}").fetchone()
            if row and int(row[0] or 0) > 0:
                return True
        except Exception:
            continue
    return False


def _list_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND sql IS NOT NULL
        ORDER BY name
        """
    ).fetchall()
    names: list[str] = []
    for (name,) in rows:
        if not name or str(name).startswith("sqlite_") or str(name).startswith("signal_events_fts"):
            continue
        names.append(str(name))
    return names


def _list_target_tables(conn) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]) for row in rows}


def _candidate_legacy_gateway_sqlite_paths(explicit_path: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    workspace = _workspace_root()
    raw_candidates = [explicit_path] if explicit_path else [
        os.environ.get("HG_GATEWAY_DB_PATH"),
        str(workspace / ".hg_demo" / "gateway" / "gateway.sqlite3") if workspace else None,
        str(workspace / "memory" / "gateway.sqlite3") if workspace else None,
    ]
    for raw in raw_candidates:
        if not raw:
            continue
        path = Path(raw).expanduser()
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen or not path.exists() or path.stat().st_size == 0:
            continue
        seen.add(key)
        candidates.append(path)
    return candidates


def _target_columns_map(conn) -> dict[str, list[str]]:
    rows = conn.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
        ORDER BY table_name, ordinal_position
        """
    ).fetchall()
    out: dict[str, list[str]] = {}
    for row in rows:
        out.setdefault(str(row[0]), []).append(str(row[1]))
    return out


def import_legacy_sqlite_gateway_if_needed(sqlite_path: str | None = None) -> dict[str, int]:
    backend = (os.environ.get("HG_GATEWAY_STORE") or "sqlite").strip().lower()
    if backend != "postgres":
        return {"imported_tables": 0, "imported_rows": 0, "skipped": 1}
    force_import = (os.environ.get("HG_DEMO_FORCE_LEGACY_IMPORT") or "").strip().lower() in {"1", "true", "yes", "on"}

    imported_tables = 0
    imported_rows = 0
    skipped_rows = 0
    failures: dict[str, str] = {}
    source_paths = _candidate_legacy_gateway_sqlite_paths(sqlite_path)
    if not source_paths:
        return {"imported_tables": 0, "imported_rows": 0, "skipped": 1}

    with get_connection() as target:
        _ensure_import_marker_table(target)
        if _has_import_marker(target, LEGACY_SQLITE_MARKER) and not force_import:
            return {"imported_tables": 0, "imported_rows": 0, "skipped": 1}

        target_tables = _list_target_tables(target)
        target_columns_map = _target_columns_map(target)
        for source_path in source_paths:
            source = sqlite3.connect(str(source_path))
            try:
                source.row_factory = sqlite3.Row
                pending = [table for table in _list_sqlite_tables(source) if table in target_tables and table in DEMO_IMPORT_TABLES]
                while pending:
                    progress = False
                    next_pending: list[str] = []
                    for table in pending:
                        try:
                            source_columns = [str(row[1]) for row in source.execute(f"PRAGMA table_info({_quote_ident(table)})").fetchall()]
                            target_columns = set(target_columns_map.get(table) or [])
                            columns = [col for col in source_columns if col in target_columns]
                            if not columns:
                                continue
                            select_sql = f"SELECT {', '.join(_quote_ident(col) for col in columns)} FROM {_quote_ident(table)}"
                            insert_sql = (
                                f"INSERT OR IGNORE INTO {_quote_ident(table)} "
                                f"({', '.join(_quote_ident(col) for col in columns)}) "
                                f"VALUES ({', '.join('?' for _ in columns)})"
                            )
                            cursor = source.execute(select_sql)
                            table_rows = 0
                            while True:
                                batch = cursor.fetchmany(250)
                                if not batch:
                                    break
                                for row in batch:
                                    try:
                                        result = target.execute(insert_sql, tuple(row[col] for col in columns))
                                        target.commit()
                                        if int(getattr(result, "rowcount", 0) or 0) > 0:
                                            table_rows += 1
                                    except Exception as exc:
                                        target.rollback()
                                        if "foreign key constraint" in str(exc).lower():
                                            skipped_rows += 1
                                            continue
                                        raise
                            failures.pop(f"{source_path}:{table}", None)
                            if table_rows:
                                imported_tables += 1
                                imported_rows += table_rows
                            progress = True
                        except Exception as exc:
                            target.rollback()
                            failures[f"{source_path}:{table}"] = str(exc)
                            next_pending.append(table)
                    if not progress and next_pending:
                        break
                    pending = next_pending
            finally:
                source.close()

        _write_import_marker(
            target,
            LEGACY_SQLITE_MARKER,
            {
                "source_paths": [str(path) for path in source_paths],
                "imported_tables": imported_tables,
                "imported_rows": imported_rows,
                "skipped_rows": skipped_rows,
                "failed_tables": failures,
                "force_import": force_import,
            },
        )
        if imported_rows > 0:
            record_major_disruption_once(
                title="Storage migration",
                summary="There was a platform interruption during the storage cutover. Some gaps from this period reflect downtime, not inactivity.",
                workspace_root=_workspace_root(),
                dedupe_key="migration:storage_cutover",
                kind="migration",
                severity="high",
                tags=["postgres", "migration", "outage", "continuity"],
                affected_entities=["all"],
                details={"imported_rows": imported_rows},
                within_hours=72,
            )
    return {"imported_tables": imported_tables, "imported_rows": imported_rows, "skipped_rows": skipped_rows, "failed_tables": failures, "skipped": 0}


def import_legacy_file_runtime_if_needed() -> dict[str, int]:
    backend = (os.environ.get("HG_GATEWAY_STORE") or "sqlite").strip().lower()
    if backend != "postgres":
        return {"timeseries": 0, "decisions": 0, "latest_state": 0, "skipped": 1}

    root = _workspace_root()
    if not root:
        return {"timeseries": 0, "decisions": 0, "latest_state": 0, "skipped": 1}

    from hg_gateway.shared_storage import (
        append_agent_decision,
        append_overseer_timeseries,
        list_agent_decisions,
        list_overseer_timeseries,
        upsert_latest_overseer_state,
    )

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        if _has_import_marker(conn, LEGACY_FILE_MARKER) and not _legacy_file_runtime_import_still_needed(conn, root):
            return {"timeseries": 0, "decisions": 0, "latest_state": 0, "skipped": 1}

    imported_timeseries = 0
    imported_decisions = 0
    imported_latest = 0

    overseer_dir = root / "memory" / "overseer"
    latest_path = overseer_dir / "latest_state.json"
    if latest_path.exists():
        try:
            payload = json.loads(latest_path.read_text(encoding="utf-8"))
            upsert_latest_overseer_state(payload)
            imported_latest = 1
        except Exception:
            pass

    if not list_overseer_timeseries(limit=1):
        timeseries_path = overseer_dir / "timeseries.jsonl"
        if timeseries_path.exists():
            try:
                with timeseries_path.open(encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        payload = json.loads(line)
                        append_overseer_timeseries(payload)
                        imported_timeseries += 1
            except Exception:
                imported_timeseries = 0

    automation_dir = root / "memory" / "automation"
    if automation_dir.exists():
        for session_dir in automation_dir.iterdir():
            if not session_dir.is_dir():
                continue
            decisions_path = session_dir / "decisions.json"
            if not decisions_path.exists():
                continue
            agent_id = session_dir.name.replace("automation-", "", 1)
            try:
                payload = json.loads(decisions_path.read_text(encoding="utf-8"))
                legacy_items = payload.get("decisions", [])
                if not isinstance(legacy_items, list):
                    continue
                current_count = len(list_agent_decisions(agent_id, limit=max(len(legacy_items) + 5, 10)))
                if current_count >= len(legacy_items):
                    continue
            except Exception:
                try:
                    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
                    legacy_items = payload.get("decisions", [])
                except Exception:
                    continue
            try:
                for item in legacy_items:
                    append_agent_decision(
                        decision_id=str(item.get("decision_id") or item.get("id") or f"{agent_id}-{imported_decisions + 1}"),
                        agent_id=agent_id,
                        timestamp=str(item.get("timestamp") or item.get("created_at") or ""),
                        action=str(item.get("action") or ""),
                        rationale=str(item.get("rationale") or ""),
                        alternatives=item.get("alternatives") or [],
                        tradeoffs=item.get("tradeoffs"),
                        context=item.get("context"),
                        outcome=item.get("outcome"),
                    )
                    imported_decisions += 1
            except Exception:
                continue

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        _write_import_marker(
            conn,
            LEGACY_FILE_MARKER,
            {"timeseries": imported_timeseries, "decisions": imported_decisions, "latest_state": imported_latest},
        )
    return {"timeseries": imported_timeseries, "decisions": imported_decisions, "latest_state": imported_latest, "skipped": 0}


def _legacy_file_runtime_import_still_needed(conn, root: Path) -> bool:
    try:
        row = conn.execute("SELECT COUNT(*) FROM agent_decisions").fetchone()
        live_decisions = int(row[0] or 0) if row else 0
        if live_decisions == 0:
            return True
        legacy_decisions = 0
        automation_dir = root / "memory" / "automation"
        if automation_dir.exists():
            for session_dir in automation_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                decisions_path = session_dir / "decisions.json"
                if not decisions_path.exists():
                    continue
                try:
                    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
                    legacy_decisions += len(payload.get("decisions", []))
                except Exception:
                    continue
        if legacy_decisions > live_decisions:
            return True
    except Exception:
        return True
    try:
        latest = conn.execute("SELECT COUNT(*) FROM overseer_latest_state").fetchone()
        if latest and int(latest[0] or 0) == 0:
            return True
    except Exception:
        return True
    return False


def import_legacy_runs_if_needed() -> dict[str, int]:
    backend = (os.environ.get("HG_GATEWAY_STORE") or "sqlite").strip().lower()
    if backend != "postgres":
        return {"discovered": 0, "inserted": 0, "updated": 0, "skipped": 1}

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        if _has_import_marker(conn, LEGACY_RUNS_MARKER):
            return {"discovered": 0, "inserted": 0, "updated": 0, "skipped": 1}

    from operator_console.server.app.services.run_index_db import backfill_discovered_runs

    result = backfill_discovered_runs(limit=20000)
    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        _write_import_marker(conn, LEGACY_RUNS_MARKER, result)
    return {**result, "skipped": 0}


def ensure_demo_tenant_settings() -> None:
    try:
        from hg_gateway.store import get_store
    except Exception:
        return
    store = get_store()
    existing = getattr(store, "get_tenant_settings", lambda _tenant_id: None)("default") or {}
    approval_rules = existing.get("approval_rules") if isinstance(existing.get("approval_rules"), list) else []
    existing_ids = {str(rule.get("id") or "").strip() for rule in approval_rules if isinstance(rule, dict)}
    merged_rules = list(approval_rules)
    for rule in DEMO_SOCIAL_APPROVAL_RULES:
        rule_id = str(rule.get("id") or "").strip()
        if rule_id and rule_id in existing_ids:
            continue
        merged_rules.append(rule)
    if merged_rules == approval_rules:
        return
    store.tenant_settings_upsert(
        "default",
        approval_rules=merged_rules,
    )


def backfill_operational_state_if_needed() -> dict[str, int]:
    backend = (os.environ.get("HG_GATEWAY_STORE") or "sqlite").strip().lower()
    if backend != "postgres":
        return {"state_keys": 0, "skipped": 1}

    from hg_gateway.shared_storage import put_operational_state
    from hg_lib.json_compat import load_path_lenient

    root = _workspace_root()
    if not root:
        return {"state_keys": 0, "skipped": 1}

    mappings = {
        "social:known_agents": root / "memory" / "automation" / "known_agents.json",
        "social:conversation_threads": root / "memory" / "automation" / "conversation_threads.json",
        "social:cross_platform_topics": root / "memory" / "automation" / "cross_platform_topics.json",
        "social:blocked_users": root / "memory" / "automation" / "blocked_users.json",
        "social:topic_history": root / "memory" / "automation" / "topic_history.json",
        "social:phrase_history": root / "memory" / "automation" / "phrase_history.json",
    }
    defaults = {
        "social:known_agents": {"known_agents": {}},
        "social:conversation_threads": {"threads": {}, "version": "1.0"},
        "social:cross_platform_topics": {"topics": []},
        "social:blocked_users": {"blocked_users": []},
        "social:topic_history": {"topics": [], "last_updated": "", "version": "1.0"},
        "social:phrase_history": {"phrases": [], "last_updated": "", "version": "1.0"},
    }

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        if _has_import_marker(conn, LEGACY_SOCIAL_STATE_MARKER):
            return {"state_keys": 0, "skipped": 1}

    count = 0
    for state_key, path in mappings.items():
        payload = load_path_lenient(path, defaults[state_key])
        if payload is None:
            payload = defaults[state_key]
        put_operational_state(state_key, payload)
        count += 1

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        _write_import_marker(conn, LEGACY_SOCIAL_STATE_MARKER, {"state_keys": count})
    return {"state_keys": count, "skipped": 0}


def backfill_memory_graphs_if_needed() -> dict[str, int]:
    backend = (os.environ.get("HG_GATEWAY_STORE") or "sqlite").strip().lower()
    if backend != "postgres":
        return {"agents": 0, "memory_entities": 0, "memory_facts": 0, "context_entities": 0, "identity_entities": 0, "skipped": 1}

    root = _workspace_root()
    if not root:
        return {"agents": 0, "memory_entities": 0, "memory_facts": 0, "context_entities": 0, "identity_entities": 0, "skipped": 1}

    from hg_memory.agent.agent_memory_indexer import AgentMemoryIndexer
    from hg_gateway.shared_storage import (
        upsert_memory_entity,
        upsert_memory_fact,
        upsert_context_entity,
        upsert_context_relation,
        upsert_identity_entity,
        upsert_identity_pattern,
        upsert_identity_relation,
        upsert_identity_version,
    )

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        force_import = (os.environ.get("HG_DEMO_FORCE_LEGACY_IMPORT") or "").strip().lower() in {"1", "true", "yes", "on"}
        if _has_import_marker(conn, LEGACY_MEMORY_MARKER) and not force_import:
            return {"agents": 0, "memory_entities": 0, "memory_facts": 0, "context_entities": 0, "identity_entities": 0, "skipped": 1}

    indexed_agents = 0
    memory_entities = 0
    memory_facts = 0
    for agent_dir in sorted((root / "memory" / "automation").glob("automation-*")):
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name.replace("automation-", "", 1)
        if agent_id.startswith("test-") or agent_id.startswith("nonexistent-"):
            continue
        try:
            AgentMemoryIndexer(agent_id).index_all()
            indexed_agents += 1
        except Exception:
            continue
        legacy_db = agent_dir / "agent_memory.db"
        if legacy_db.exists():
            conn = sqlite3.connect(str(legacy_db))
            try:
                conn.row_factory = sqlite3.Row
                entity_rows = conn.execute(
                    "SELECT id, type, name, path, summary_excerpt, created_at, updated_at FROM entity ORDER BY id"
                ).fetchall()
                entity_id_map: dict[int, int] = {}
                for row in entity_rows:
                    new_entity_id = upsert_memory_entity(
                        agent_id=agent_id,
                        entity_type=str(row["type"] or ""),
                        name=str(row["name"] or ""),
                        path=str(row["path"] or ""),
                        summary_excerpt=row["summary_excerpt"],
                    )
                    entity_id_map[int(row["id"])] = new_entity_id
                    memory_entities += 1
                fact_rows = conn.execute(
                    """
                    SELECT entity_id, fact, category, timestamp, source, status, related_entities_json
                    FROM fact
                    ORDER BY id
                    """
                ).fetchall()
                for row in fact_rows:
                    mapped_entity_id = entity_id_map.get(int(row["entity_id"]))
                    if not mapped_entity_id:
                        continue
                    upsert_memory_fact(
                        agent_id=agent_id,
                        entity_id=mapped_entity_id,
                        fact=str(row["fact"] or ""),
                        category=row["category"],
                        timestamp=row["timestamp"],
                        source=row["source"],
                        status=row["status"],
                        related_entities_json=row["related_entities_json"],
                    )
                    memory_facts += 1
            finally:
                conn.close()

    context_entities = 0
    context_relations = 0
    context_path = root / "memory" / "context_graph.db"
    if context_path.exists():
        conn = sqlite3.connect(str(context_path))
        try:
            conn.row_factory = sqlite3.Row
            entity_rows = conn.execute(
                """
                SELECT e.entity_id, e.entity_type, e.agent_id, e.timestamp, e.properties, f.content, f.language, f.content_normalized
                FROM context_entities e
                LEFT JOIN context_fts f ON f.entity_id = e.entity_id
                """
            ).fetchall()
            for row in entity_rows:
                upsert_context_entity(
                    entity_id=str(row["entity_id"]),
                    entity_type=str(row["entity_type"]),
                    agent_id=row["agent_id"],
                    timestamp=str(row["timestamp"] or ""),
                    properties=json.loads(row["properties"] or "{}"),
                    content=str(row["content"] or ""),
                    language=str(row["language"] or "en"),
                    content_normalized=str(row["content_normalized"] or row["content"] or ""),
                )
                context_entities += 1
            relation_rows = conn.execute(
                "SELECT relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties FROM context_relations"
            ).fetchall()
            for row in relation_rows:
                upsert_context_relation(
                    relation_id=str(row["relation_id"]),
                    from_entity_id=str(row["from_entity_id"]),
                    to_entity_id=str(row["to_entity_id"]),
                    relation_type=str(row["relation_type"]),
                    timestamp=row["timestamp"],
                    properties=json.loads(row["properties"] or "{}"),
                )
                context_relations += 1
        finally:
            conn.close()

    identity_entities = 0
    identity_versions = 0
    for identity_path in sorted((root / "memory" / "automation").glob("automation-*/identity_graph.db")):
        agent_scope = identity_path.parent.name.replace("automation-", "", 1)
        conn = sqlite3.connect(str(identity_path))
        try:
            conn.row_factory = sqlite3.Row
            entity_rows = conn.execute(
                """
                SELECT e.entity_id, e.entity_type, e.agent_id, e.platform, e.timestamp, e.properties, f.content, f.language, f.content_normalized
                FROM identity_entities e
                LEFT JOIN identity_fts f ON f.entity_id = e.entity_id
                """
            ).fetchall()
            for row in entity_rows:
                entity_id = f"{agent_scope}:{row['entity_id']}"
                upsert_identity_entity(
                    entity_id=entity_id,
                    entity_type=str(row["entity_type"]),
                    agent_id=row["agent_id"],
                    platform=row["platform"],
                    timestamp=str(row["timestamp"] or ""),
                    properties=json.loads(row["properties"] or "{}"),
                    content=str(row["content"] or ""),
                    language=str(row["language"] or "en"),
                    content_normalized=str(row["content_normalized"] or row["content"] or ""),
                )
                identity_entities += 1
            relation_rows = conn.execute(
                "SELECT relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties FROM identity_relations"
            ).fetchall()
            for row in relation_rows:
                upsert_identity_relation(
                    relation_id=f"{agent_scope}:{row['relation_id']}",
                    from_entity_id=f"{agent_scope}:{row['from_entity_id']}",
                    to_entity_id=f"{agent_scope}:{row['to_entity_id']}",
                    relation_type=str(row["relation_type"]),
                    timestamp=row["timestamp"],
                    properties=json.loads(row["properties"] or "{}"),
                )
            version_rows = conn.execute(
                "SELECT version_id, persona_file, content_hash, platform, persona_set, agent_id, timestamp, diff_before, diff_after FROM identity_versions"
            ).fetchall()
            for row in version_rows:
                upsert_identity_version(
                    version_id=f"{agent_scope}:{row['version_id']}",
                    persona_file=str(row["persona_file"]),
                    content_hash=str(row["content_hash"]),
                    platform=row["platform"],
                    persona_set=row["persona_set"],
                    agent_id=row["agent_id"],
                    timestamp=str(row["timestamp"] or ""),
                    diff_before=row["diff_before"],
                    diff_after=row["diff_after"],
                )
                identity_versions += 1
            pattern_rows = conn.execute(
                "SELECT pattern_id, pattern_type, agent_id, platform, timestamp, properties FROM identity_patterns"
            ).fetchall()
            for row in pattern_rows:
                upsert_identity_pattern(
                    pattern_id=f"{agent_scope}:{row['pattern_id']}",
                    pattern_type=str(row["pattern_type"]),
                    agent_id=row["agent_id"],
                    platform=row["platform"],
                    timestamp=str(row["timestamp"] or ""),
                    properties=json.loads(row["properties"] or "{}"),
                )
        finally:
            conn.close()

    with get_connection() as conn:
        _ensure_import_marker_table(conn)
        _write_import_marker(
            conn,
            LEGACY_MEMORY_MARKER,
            {
                "indexed_agents": indexed_agents,
                "memory_entities": memory_entities,
                "memory_facts": memory_facts,
                "context_entities": context_entities,
                "context_relations": context_relations,
                "identity_entities": identity_entities,
                "identity_versions": identity_versions,
            },
        )
    return {
        "agents": indexed_agents,
        "memory_entities": memory_entities,
        "memory_facts": memory_facts,
        "context_entities": context_entities,
        "context_relations": context_relations,
        "identity_entities": identity_entities,
        "identity_versions": identity_versions,
        "skipped": 0,
    }


def sync_runs_from_disk_to_db() -> dict:
    """Insert any runs found on disk (dag_runs, runs_root) into the shared runs table. Additive only — never wipes or truncates. DB is primary; disk is backup. Idempotent."""
    try:
        from operator_console.server.app.services.run_index_db import backfill_discovered_runs
        return backfill_discovered_runs(limit=20000)
    except Exception:
        return {"discovered": 0, "inserted": 0, "updated": 0}


def ensure_demo_governance() -> None:
    """Seed release verdicts and one constitutional root so governance page and gate 'just work' in demo."""
    try:
        from hg_core.gate import create_release_verdict
        from hg_core.constitutional_memory import upsert_constitutional_root
    except Exception:
        return
    env = os.environ.get("HG_ENV", "demo").strip().lower() or "demo"
    workflow_families = [
        "social",
        "social-media",
        "overseer-monitor",
        "fourclaw-auto-post-cadence",
        "fourclaw-engage",
        "moltbook-auto-post",
        "moltbook-engage",
        "moltx-auto-post",
        "moltx-engage",
        "aichan-auto-post",
        "aichan-engage",
        "agentchan-auto-post",
        "agentchan-engage",
        "memory-maintenance",
        "knowledge-research-auto",
        "knowledge-research-auto-v2",
        "moltstack-draft",
        "moltstack-publish",
        "rcmp-job-search-monitor",
        "phase10-smoke",
    ]
    for wf in workflow_families:
        try:
            create_release_verdict(
                workflow_family=wf,
                target_kind="workflow",
                target_id=wf,
                evaluation_id=None,
                verdict="eligible",
                reason="Demo seed",
                stale_after_hours=24 * 7,
                tenant_id="default",
            )
        except Exception:
            pass
    try:
        upsert_constitutional_root(
            root_id="demo-social-root",
            workflow_family="social",
            title="Social constitutional root",
            root_goal="Advance the remit without losing judgment.",
            material_constraints=["Do not spam", "Do not drift off remit"],
            approved_subgoals=["Build relationships", "Gather signal when needed"],
            status="active",
            tenant_id="default",
        )
    except Exception:
        pass
    try:
        upsert_constitutional_root(
            root_id="demo-social-media-root",
            workflow_family="social-media",
            title="Unified social constitutional root",
            root_goal="Advance the remit through the unified social cadence without losing judgment.",
            material_constraints=["Do not spam", "Do not drift off remit"],
            approved_subgoals=["Build relationships", "Gather signal when needed"],
            status="active",
            tenant_id="default",
        )
    except Exception:
        pass


def main() -> int:
    from hg_gateway.principals import list_principals, upsert_principal

    import_legacy_sqlite_gateway_if_needed()
    import_legacy_file_runtime_if_needed()
    import_legacy_runs_if_needed()
    backfill_operational_state_if_needed()
    backfill_memory_graphs_if_needed()
    ensure_demo_tenant_settings()
    ensure_demo_governance()
    try:
        from demo.seed_journey_fixtures import seed_journey_fixtures
        from hg_lib.config import get_workspace_root

        ws = get_workspace_root()
        if ws is not None:
            seed_journey_fixtures(ws)
    except Exception:
        pass
    # One-time disk→DB import was run via: docker exec <api> python -m hg_gateway.seed_demo
    # Do not auto-import; primary is Postgres. To re-import: call sync_runs_from_disk_to_db() manually.

    existing = list_principals("default", include_disabled=True)
    if existing:
        return 0
    upsert_principal(
        "default",
        "user",
        "Demo Principal",
        tenant_id="default",
        status="offline",
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"seed_demo: {e}", file=sys.stderr)
        sys.exit(1)
