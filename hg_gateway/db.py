"""
SQLite database and migrations for gateway persistence.
Schema version is stored in _schema_version table; migrations run on open.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from hg_gateway.llm_defaults import get_default_model, get_default_provider
from hg_gateway.storage_config import gateway_db_path, gateway_requires_postgres, gateway_store_backend

SCHEMA_VERSION = 55


def _backend() -> str:
    return gateway_store_backend()


def _get_db_path() -> str:
    return gateway_db_path()


def _normalize_db_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _ensure_dir(path: str) -> Path:
    normalized = _normalize_db_path(path)
    normalized.parent.mkdir(parents=True, exist_ok=True)
    return normalized


@contextmanager
def get_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    backend = _backend()
    if gateway_requires_postgres() and backend != "postgres":
        raise RuntimeError("HG_GATEWAY_REQUIRE_POSTGRES=1 requires HG_GATEWAY_STORE=postgres")
    if backend == "postgres":
        from hg_gateway.db_postgres import get_postgres_connection

        with get_postgres_connection() as conn:
            yield conn
        return
    path = db_path or _get_db_path()
    normalized = _ensure_dir(path)
    try:
        normalized.touch(exist_ok=True)
        conn = sqlite3.connect(str(normalized))
    except OSError as exc:
        raise RuntimeError(
            f"Unable to open gateway database at {normalized} (parent={normalized.parent})"
        ) from exc
    conn.row_factory = sqlite3.Row
    try:
        _migrate(conn)
        try:
            from hg_gateway.content_cms import ensure_content_registry_seed

            ensure_content_registry_seed(conn)
        except Exception:
            pass
        try:
            from hg_gateway.tool_registry import ensure_tool_registry_seed

            ensure_tool_registry_seed(conn)
        except Exception:
            pass
        try:
            from hg_gateway.artifact_registry import ensure_artifact_registry_seed

            ensure_artifact_registry_seed(conn)
        except Exception:
            pass
        try:
            from hg_gateway.task_registry import ensure_task_registry_seed

            ensure_task_registry_seed(conn)
        except Exception:
            pass
        try:
            from hg_gateway.source_blob_registry import ensure_source_blob_registry_seed

            ensure_source_blob_registry_seed(conn)
        except Exception:
            pass
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS _schema_version (
           version INTEGER NOT NULL PRIMARY KEY,
           applied_at TEXT NOT NULL
        )"""
    )
    conn.commit()

    row = conn.execute("SELECT MAX(version) AS v FROM _schema_version").fetchone()
    current = (row["v"] or 0) if row else 0

    if current < 1:
        conn.executescript(_schema_v1())
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (1, datetime('now'))"
        )
        conn.commit()
    if current < 2:
        conn.executescript(_schema_v2())
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (2, datetime('now'))"
        )
        conn.commit()
    if current < 3:
        conn.executescript(_schema_v3())
        # Add assigned_principal_id to approvals for escalation routing
        cols = [row[1] for row in conn.execute("PRAGMA table_info(approvals)").fetchall()]
        if "assigned_principal_id" not in cols:
            conn.execute("ALTER TABLE approvals ADD COLUMN assigned_principal_id TEXT")
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (3, datetime('now'))"
        )
        conn.commit()
    if current < 4:
        conn.executescript(_schema_v4())
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (4, datetime('now'))"
        )
        conn.commit()
    if current < 5:
        conn.executescript(_schema_v5())
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (5, datetime('now'))"
        )
        conn.commit()
    if current < 6:
        _migrate_v6_tenant_id(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (6, datetime('now'))"
        )
        conn.commit()
    if current < 7:
        _migrate_v7_idempotency(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (7, datetime('now'))"
        )
        conn.commit()
    if current < 8:
        _migrate_v8_prompt_registry(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (8, datetime('now'))"
        )
        conn.commit()
    if current < 9:
        _migrate_v9_quotas(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (9, datetime('now'))"
        )
        conn.commit()
    if current < 10:
        _migrate_v10_principals_disabled(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (10, datetime('now'))"
        )
        conn.commit()
    if current < 11:
        _migrate_v11_agent_lifecycle(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (11, datetime('now'))"
        )
        conn.commit()
    if current < 12:
        _migrate_v12_chat_persona_traits(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (12, datetime('now'))"
        )
        conn.commit()
    if current < 13:
        _migrate_v13_documents(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (13, datetime('now'))"
        )
        conn.commit()
    if current < 14:
        _migrate_v14_tenant_domains_branding(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (14, datetime('now'))"
        )
        conn.commit()
    if current < 15:
        _migrate_v15_tenant_api_keys(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (15, datetime('now'))"
        )
        conn.commit()
    if current < 16:
        _migrate_v16_scheduled_jobs(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (16, datetime('now'))"
        )
        conn.commit()
    if current < 17:
        _migrate_v17_signal_events(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (17, datetime('now'))"
        )
        conn.commit()
    if current < 18:
        _migrate_v18_steering_profiles(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (18, datetime('now'))"
        )
        conn.commit()
    if current < 19:
        _migrate_v19_monitor_rules(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (19, datetime('now'))"
        )
        conn.commit()
    if current < 20:
        _migrate_v20_sessions_scim(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (20, datetime('now'))"
        )
        conn.commit()
    if current < 21:
        _migrate_v21_retention(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (21, datetime('now'))"
        )
        conn.commit()
    if current < 22:
        _migrate_v22_swarm_run(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (22, datetime('now'))"
        )
        conn.commit()
    if current < 23:
        _migrate_v23_approval_policy(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (23, datetime('now'))"
        )
        conn.commit()
    if current < 24:
        _migrate_v24_event_stream_evidence_ledger(conn)
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (24, datetime('now'))"
        )
        conn.commit()
    if current < 25:
        _migrate_v25_chat_archive(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (25, datetime('now'))"
        )
        conn.commit()
    if current < 26:
        _migrate_v26_chat_tombstones(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (26, datetime('now'))"
        )
        conn.commit()
    if current < 27:
        _migrate_v27_temporary_persona(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (27, datetime('now'))"
        )
        conn.commit()
    if current < 28:
        _migrate_v28_entity_tools_social(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (28, datetime('now'))"
        )
        conn.commit()
    if current < 29:
        _migrate_v29_chat_persona_state(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (29, datetime('now'))"
        )
        conn.commit()
    if current < 30:
        _migrate_v30_persona_naturalness_analytics(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (30, datetime('now'))"
        )
        conn.commit()
    if current < 31:
        _migrate_v31_chat_persona_autonomy_state(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (31, datetime('now'))"
        )
        conn.commit()
    if current < 32:
        _migrate_v32_persona_autonomy_analytics(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (32, datetime('now'))"
        )
        conn.commit()
    if current < 33:
        _migrate_v33_run_index(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (33, datetime('now'))"
        )
        conn.commit()
    if current < 34:
        _migrate_v34_l10_events(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (34, datetime('now'))"
        )
        conn.commit()
    if current < 35:
        _migrate_v35_run_leases(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (35, datetime('now'))"
        )
        conn.commit()
    if current < 36:
        _migrate_v36_persona_catalog(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (36, datetime('now'))"
        )
        conn.commit()
    if current < 37:
        _migrate_v37_steering_store(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (37, datetime('now'))"
        )
        conn.commit()
    if current < 38:
        _migrate_v38_knowledge_documents(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (38, datetime('now'))"
        )
        conn.commit()
    if current < 39:
        _migrate_v39_memory_graphs(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (39, datetime('now'))"
        )
        conn.commit()
    if current < 40:
        _migrate_v40_memory_context_identity(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (40, datetime('now'))"
        )
        conn.commit()
    if current < 41:
        _migrate_v41_operational_history(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (41, datetime('now'))"
        )
        conn.commit()
    if current < 42:
        _migrate_v42_agent_decisions(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (42, datetime('now'))"
        )
        conn.commit()
    if current < 43:
        _migrate_v43_approval_rules(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (43, datetime('now'))"
        )
        conn.commit()
    if current < 44:
        _migrate_v44_operational_state(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (44, datetime('now'))"
        )
        conn.commit()
    if current < 45:
        _migrate_v45_governance_spine(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (45, datetime('now'))"
        )
        conn.commit()
    if current < 46:
        _migrate_v46_governed_research_surface(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (46, datetime('now'))"
        )
        conn.commit()
    if current < 47:
        _migrate_v47_runs_blocked_reason(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (47, datetime('now'))"
        )
        conn.commit()
    if current < 48:
        _migrate_v48_runs_pending_request(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (48, datetime('now'))"
        )
        conn.commit()
    if current < 49:
        _migrate_v49_human_notifications(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (49, datetime('now'))"
        )
        conn.commit()
    if current < 50:
        _migrate_v50_commitment_records(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (50, datetime('now'))"
        )
        conn.commit()
    if current < 51:
        _migrate_v51_content_documents(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (51, datetime('now'))"
        )
        conn.commit()
    if current < 52:
        _migrate_v52_tool_registry(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (52, datetime('now'))"
        )
        conn.commit()
    if current < 53:
        _migrate_v53_artifact_registry(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (53, datetime('now'))"
        )
        conn.commit()
    if current < 54:
        _migrate_v54_task_registry(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (54, datetime('now'))"
        )
        conn.commit()
    if current < 55:
        _migrate_v55_source_blob_registry(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (55, datetime('now'))"
        )
        conn.commit()


def _schema_v1() -> str:
    return """
    CREATE TABLE IF NOT EXISTS chats (
        chat_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        unread_count INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        content TEXT NOT NULL,
        agent_id TEXT,
        tool_name TEXT,
        tool_payload TEXT,
        tool_result TEXT,
        approvals_required INTEGER,
        FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
    );
    CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);

    CREATE TABLE IF NOT EXISTS agents (
        chat_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        label TEXT NOT NULL,
        status TEXT NOT NULL,
        parent_agent_id TEXT,
        PRIMARY KEY (chat_id, agent_id),
        FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
    );

    CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        status TEXT NOT NULL,
        kind TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        risk TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        payload TEXT NOT NULL,
        resolution_note TEXT,
        chat_id TEXT
    );

    CREATE TABLE IF NOT EXISTS approval_chat_lock (
        approval_id TEXT PRIMARY KEY,
        chat_id TEXT NOT NULL,
        FOREIGN KEY (approval_id) REFERENCES approvals(id)
    );

    CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_events_chat_id ON events(chat_id);
    CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(chat_id, created_at);
    """


def _schema_v2() -> str:
    """entity_summaries for trait judge memory summary cache."""
    return """
    CREATE TABLE IF NOT EXISTS entity_summaries (
        entity_id TEXT NOT NULL PRIMARY KEY,
        summary_text TEXT NOT NULL,
        key_facts TEXT NOT NULL,
        conflicts TEXT NOT NULL,
        evidence_ids TEXT NOT NULL,
        evidence_hash TEXT,
        updated_at TEXT NOT NULL
    );
    """


def _schema_v3() -> str:
    """Principals and availability (Pack2-08); assigned_principal_id on approvals."""
    return """
    CREATE TABLE IF NOT EXISTS principals (
        id TEXT NOT NULL PRIMARY KEY,
        type TEXT NOT NULL,
        label TEXT NOT NULL,
        timezone TEXT,
        on_call_hours TEXT,
        status TEXT NOT NULL DEFAULT 'offline',
        escalation_chain TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """


def _schema_v4() -> str:
    """Step-up auth (Pack2-06): TOTP secrets and challenges."""
    return """
    CREATE TABLE IF NOT EXISTS stepup_secrets (
        user_id TEXT NOT NULL PRIMARY KEY,
        encrypted_secret TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS stepup_challenges (
        challenge_id TEXT NOT NULL PRIMARY KEY,
        user_id TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    """


def _schema_v5() -> str:
    """Situational testbed (Pack2-05): probe runs and results."""
    return """
    CREATE TABLE IF NOT EXISTS probe_runs (
        run_id TEXT NOT NULL PRIMARY KEY,
        suite TEXT NOT NULL,
        config_json TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS probe_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        probe_id TEXT NOT NULL,
        probe_type TEXT NOT NULL,
        outcome TEXT NOT NULL,
        input_hash TEXT,
        output_snippet TEXT,
        evidence TEXT,
        rationale TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES probe_runs(run_id)
    );
    CREATE INDEX IF NOT EXISTS idx_probe_results_run_id ON probe_results(run_id);
    """


def _migrate_v6_tenant_id(conn: sqlite3.Connection) -> None:
    """Pack3: Add tenant_id to all tables for multi-tenant boundaries. Default 'default' for existing rows."""
    tables_columns = [
        ("chats", "tenant_id"),
        ("messages", "tenant_id"),
        ("agents", "tenant_id"),
        ("approvals", "tenant_id"),
        ("approval_chat_lock", "tenant_id"),
        ("events", "tenant_id"),
        ("entity_summaries", "tenant_id"),
        ("principals", "tenant_id"),
        ("stepup_secrets", "tenant_id"),
        ("stepup_challenges", "tenant_id"),
        ("probe_runs", "tenant_id"),
        ("probe_results", "tenant_id"),
    ]
    for table, col in tables_columns:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT 'default'")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    # Composite indexes for tenant-scoped queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_tenant_id ON chats(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_tenant_chat ON messages(tenant_id, chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agents_tenant_chat ON agents(tenant_id, chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_tenant_id ON approvals(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_tenant_chat ON events(tenant_id, chat_id)")
    # Audit log for cross-tenant and security events
    conn.execute(
        """CREATE TABLE IF NOT EXISTS audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_id ON audit_events(tenant_id)")


def _migrate_v7_idempotency(conn: sqlite3.Connection) -> None:
    """Pack3 Phase 2: Idempotency and tool effect dedupe."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS idempotency_records (
        tenant_id TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        route TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        response_body TEXT NOT NULL,
        response_status INTEGER NOT NULL DEFAULT 200,
        created_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, idempotency_key)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tool_effect_ledger (
        tenant_id TEXT NOT NULL,
        effects_hash TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, effects_hash)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_tenant_key ON idempotency_records(tenant_id, idempotency_key)")


def _migrate_v8_prompt_registry(conn: sqlite3.Connection) -> None:
    """Pack3 Phase 6: Prompt and model registry; turn provenance per message."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS prompts (
        id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        version TEXT NOT NULL,
        body TEXT NOT NULL,
        owner TEXT NOT NULL DEFAULT 'system',
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prompts_tenant ON prompts(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS model_configs (
        id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        version TEXT NOT NULL,
        model_id TEXT NOT NULL,
        params_json TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_model_configs_tenant ON model_configs(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS turn_provenance (
        message_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        prompt_id TEXT NOT NULL,
        model_config_id TEXT NOT NULL,
        sampling_params_json TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_provenance_tenant ON turn_provenance(tenant_id)")
    # Seed default prompt and model config
    conn.execute(
        """INSERT OR IGNORE INTO prompts (id, tenant_id, name, version, body, owner, created_at)
           VALUES ('default', 'default', 'default', '1', 'You are a helpful assistant.', 'system', datetime('now'))"""
    )
    conn.execute(
        """INSERT OR IGNORE INTO model_configs (id, tenant_id, version, model_id, params_json, created_at)
           VALUES (?, 'default', '1', ?, ?, datetime('now'))""",
        (
            "default",
            get_default_model(get_default_provider()),
            json.dumps({"max_tokens": 1024, "temperature": 0.7}),
        ),
    )


def _migrate_v9_quotas(conn: sqlite3.Connection) -> None:
    """Pack4: Tenant quotas and usage for rate, streams, tool concurrency, storage."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_quotas (
        tenant_id TEXT NOT NULL PRIMARY KEY,
        limits_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_usage (
        tenant_id TEXT NOT NULL PRIMARY KEY,
        counters_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL
        )"""
    )


def _migrate_v10_principals_disabled(conn: sqlite3.Connection) -> None:
    """Principals disabled flag for user management; disabled principals excluded from escalation."""
    try:
        conn.execute("ALTER TABLE principals ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise


def _migrate_v11_agent_lifecycle(conn: sqlite3.Connection) -> None:
    """Pack 10: Agent lifecycle state (active, paused, quarantined) with reason and updated_at/updated_by."""
    for col, typ in [
        ("lifecycle_state", "TEXT NOT NULL DEFAULT 'active'"),
        ("state_reason", "TEXT"),
        ("state_updated_at", "TEXT"),
        ("state_updated_by", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE agents ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise


def _migrate_v12_chat_persona_traits(conn: sqlite3.Connection) -> None:
    """Phase 7.3: Chat persona (fingerprint_id, skin_id) and steering traits."""
    for col in ("fingerprint_id", "skin_id"):
        try:
            conn.execute(f"ALTER TABLE chats ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chat_traits (
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        traits_json TEXT NOT NULL DEFAULT '{}',
        PRIMARY KEY (tenant_id, chat_id)
        )"""
    )


def _migrate_v13_documents(conn: sqlite3.Connection) -> None:
    """Pack 12: Document ingestion — documents, document_page, document_chunk, document_job."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        chat_id TEXT,
        filename TEXT NOT NULL,
        mime TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_by TEXT,
        parse_status TEXT NOT NULL DEFAULT 'pending',
        meta_json TEXT NOT NULL DEFAULT '{}'
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_chat_id ON documents(chat_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS document_pages (
        document_id TEXT NOT NULL,
        page_no INTEGER NOT NULL,
        text TEXT NOT NULL,
        sha256 TEXT,
        PRIMARY KEY (document_id, page_no)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS document_chunks (
        chunk_id TEXT NOT NULL PRIMARY KEY,
        document_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        text TEXT NOT NULL,
        tokens_est INTEGER NOT NULL,
        page_start INTEGER NOT NULL,
        page_end INTEGER NOT NULL,
        chunk_sha256 TEXT,
        provenance_json TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_tenant_id ON document_chunks(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS document_jobs (
        job_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        ended_at TEXT,
        error TEXT,
        document_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_jobs_tenant_id ON document_jobs(tenant_id)")


def _migrate_v14_tenant_domains_branding(conn: sqlite3.Connection) -> None:
    """Pack 13: Tenant domains and branding — tenant_settings, tenant_domains for host-based white-label."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_settings (
        tenant_id TEXT NOT NULL PRIMARY KEY,
        display_name TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        logo_artifact_id TEXT,
        theme_json TEXT NOT NULL DEFAULT '{}',
        support_links_json TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_domains (
        hostname TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_domains_tenant_id ON tenant_domains(tenant_id)")
    # Seed default tenant for branding
    conn.execute(
        """INSERT OR IGNORE INTO tenant_settings (tenant_id, display_name, status, theme_json, support_links_json, updated_at)
           VALUES ('default', 'Default', 'active', '{}', '[]', datetime('now'))"""
    )


def _migrate_v15_tenant_api_keys(conn: sqlite3.Connection) -> None:
    """Pack 13: Tenant API keys (hash stored; raw key shown only once at create)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_api_keys (
        id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_tenant_id ON tenant_api_keys(tenant_id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_api_keys_hash ON tenant_api_keys(key_hash)")


def _migrate_v16_scheduled_jobs(conn: sqlite3.Connection) -> None:
    """Pack 14: Schedule API — scheduled_jobs (tenant-scoped), schedule_run_requests for run_once."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scheduled_jobs (
        tenant_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        cron TEXT,
        interval_minutes REAL,
        inputs_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, job_id),
        CHECK ((cron IS NOT NULL AND interval_minutes IS NULL) OR (cron IS NULL AND interval_minutes IS NOT NULL))
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_tenant_id ON scheduled_jobs(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schedule_run_requests (
        id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        requested_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_run_requests_status ON schedule_run_requests(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_run_requests_tenant_job ON schedule_run_requests(tenant_id, job_id)")


def _migrate_v17_signal_events(conn: sqlite3.Connection) -> None:
    """Pack 15: Latent signals — signal_events, signal_features, FTS5 for event search."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS signal_events (
        event_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        chat_id TEXT,
        turn_id TEXT,
        entity_id TEXT,
        direction TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        signals_json TEXT NOT NULL,
        text_sha256 TEXT,
        provenance_json TEXT,
        trace_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_events_tenant_id ON signal_events(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_events_chat_id ON signal_events(chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_events_entity_id ON signal_events(entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_events_timestamp ON signal_events(tenant_id, timestamp)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS signal_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        feature_key TEXT NOT NULL,
        feature_value REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES signal_events(event_id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_features_event_id ON signal_features(event_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_features_tenant_key ON signal_features(tenant_id, feature_key)")
    # FTS5 virtual table for event search; insert rows when inserting signal_events (tags/explanation from signals_json)
    conn.execute(
        """CREATE VIRTUAL TABLE IF NOT EXISTS signal_events_fts USING fts5(
        event_id,
        tenant_id,
        chat_id,
        entity_id,
        tags,
        explanation,
        tokenize='unicode61'
        )"""
    )


def _migrate_v18_steering_profiles(conn: sqlite3.Connection) -> None:
    """Pack 15.3: Steering profiles and lenses — profile model, per-tenant/chat override."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS steering_profiles (
        profile_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT,
        type TEXT NOT NULL,
        strength REAL NOT NULL DEFAULT 0.5,
        target_json TEXT,
        prompt_fragments_json TEXT,
        classifier_thresholds_json TEXT,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_steering_profiles_tenant_id ON steering_profiles(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_default_steering (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (tenant_id, profile_id),
        FOREIGN KEY (profile_id) REFERENCES steering_profiles(profile_id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_default_steering_tenant ON tenant_default_steering(tenant_id)")
    # Per-chat override: store profile_ids on chat
    cols = [row[1] for row in conn.execute("PRAGMA table_info(chats)").fetchall()]
    if "steering_profile_ids" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN steering_profile_ids TEXT")


def _migrate_v19_monitor_rules(conn: sqlite3.Connection) -> None:
    """Pack 15.4: Monitoring rules for Pack 10 — condition engine, cooldown."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS monitor_rules (
        rule_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT,
        enabled INTEGER NOT NULL DEFAULT 1,
        condition_json TEXT NOT NULL,
        action TEXT NOT NULL,
        message_template TEXT,
        cooldown_seconds INTEGER NOT NULL DEFAULT 60,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_monitor_rules_tenant_id ON monitor_rules(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rule_last_triggered (
        rule_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        last_triggered_at TEXT NOT NULL,
        PRIMARY KEY (rule_id, tenant_id, chat_id)
        )"""
    )


def _migrate_v20_sessions_scim(conn: sqlite3.Connection) -> None:
    """Pack 16: OIDC session store and SCIM users/groups for enterprise identity."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        principal_id TEXT NOT NULL,
        roles_json TEXT NOT NULL,
        csrf_token TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        idp_sub TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_tenant_id ON sessions(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scim_users (
        id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        external_id TEXT,
        user_name TEXT NOT NULL,
        display_name TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        meta_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scim_users_tenant_id ON scim_users(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scim_groups (
        id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        meta_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scim_groups_tenant_id ON scim_groups(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scim_group_members (
        group_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        PRIMARY KEY (group_id, user_id),
        FOREIGN KEY (group_id) REFERENCES scim_groups(id),
        FOREIGN KEY (user_id) REFERENCES scim_users(id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scim_group_role_mapping (
        tenant_id TEXT NOT NULL,
        group_id TEXT NOT NULL,
        role TEXT NOT NULL,
        PRIMARY KEY (tenant_id, group_id, role)
        )"""
    )


def _migrate_v21_retention(conn: sqlite3.Connection) -> None:
    """Pack 17: Per-tenant retention policy and legal hold."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenant_retention (
        tenant_id TEXT NOT NULL PRIMARY KEY,
        chats_days INTEGER NOT NULL DEFAULT 90,
        docs_days INTEGER NOT NULL DEFAULT 90,
        proofs_days INTEGER NOT NULL DEFAULT 30,
        logs_days INTEGER NOT NULL DEFAULT 30,
        legal_hold_enabled INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
        )"""
    )


def _migrate_v22_swarm_run(conn: sqlite3.Connection) -> None:
    """Swarm run identity: associate chats with swarm_run_id and swarm_role (entity | orchestrator)."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(chats)").fetchall()]
    if "swarm_run_id" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN swarm_run_id TEXT")
    if "swarm_role" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN swarm_role TEXT")


def _migrate_v23_approval_policy(conn: sqlite3.Connection) -> None:
    """Tenant approval policy: first_turn_approval_required, auto_approve_kinds (JSON array)."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(tenant_settings)").fetchall()]
    if "first_turn_approval_required" not in cols:
        conn.execute("ALTER TABLE tenant_settings ADD COLUMN first_turn_approval_required INTEGER NOT NULL DEFAULT 0")
    if "auto_approve_kinds_json" not in cols:
        conn.execute("ALTER TABLE tenant_settings ADD COLUMN auto_approve_kinds_json TEXT NOT NULL DEFAULT '[]'")


def _migrate_v43_approval_rules(conn: sqlite3.Connection) -> None:
    """Tenant approval policy extensions: targeted auto-approval rules."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(tenant_settings)").fetchall()]
    if "approval_rules_json" not in cols:
        conn.execute("ALTER TABLE tenant_settings ADD COLUMN approval_rules_json TEXT NOT NULL DEFAULT '[]'")


def _migrate_v44_operational_state(conn: sqlite3.Connection) -> None:
    """Shared JSON replacement store for remaining operational state."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS operational_state (
        state_key TEXT PRIMARY KEY,
        payload TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_operational_state_updated_at ON operational_state(updated_at)")


def _migrate_v24_event_stream_evidence_ledger(conn: sqlite3.Connection) -> None:
    """Pack 25: Unified event stream and evidence ledger (append-only, hash chain)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS event_stream (
        event_id TEXT NOT NULL PRIMARY KEY,
        ts TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        actor_type TEXT,
        actor_id TEXT,
        run_id TEXT,
        chat_id TEXT,
        turn_id TEXT,
        tool_call_id TEXT,
        approval_id TEXT,
        document_id TEXT,
        chunk_id TEXT,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL,
        prev_event_sha256 TEXT,
        event_sha256 TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_stream_tenant_ts ON event_stream(tenant_id, ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_stream_tenant_run ON event_stream(tenant_id, run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_stream_tenant_chat ON event_stream(tenant_id, chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_stream_event_type ON event_stream(event_type)")


def _migrate_v25_chat_archive(conn: sqlite3.Connection) -> None:
    """Client lifecycle: soft archive chats and swarm groups, plus list filtering."""
    for col, typ in [
        ("archived_at", "TEXT"),
        ("archive_reason", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE chats ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_tenant_archived_at ON chats(tenant_id, archived_at)")

    conn.execute(
        """CREATE TABLE IF NOT EXISTS evidence_ledger (
        ledger_id TEXT NOT NULL PRIMARY KEY,
        ts TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        run_id TEXT,
        chat_id TEXT,
        turn_id TEXT,
        tool_call_id TEXT,
        approval_id TEXT,
        document_id TEXT,
        chunk_id TEXT,
        evidence_type TEXT NOT NULL,
        content_sha256 TEXT NOT NULL,
        content_ref TEXT,
        content_bytes BLOB,
        redaction_applied TEXT,
        prev_ledger_sha256 TEXT,
        ledger_sha256 TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_ledger_tenant_ts ON evidence_ledger(tenant_id, ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_ledger_tenant_run ON evidence_ledger(tenant_id, run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_ledger_tenant_chat ON evidence_ledger(tenant_id, chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_ledger_evidence_type ON evidence_ledger(evidence_type)")


def _migrate_v26_chat_tombstones(conn: sqlite3.Connection) -> None:
    """Client lifecycle: soft-delete tombstones with restore windows for chats and swarm groups."""
    for col, typ in [
        ("deleted_at", "TEXT"),
        ("delete_reason", "TEXT"),
        ("restore_deadline_at", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE chats ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_tenant_deleted_at ON chats(tenant_id, deleted_at)")


def _migrate_v27_temporary_persona(conn: sqlite3.Connection) -> None:
    """Turn-scoped persona steering for chat sessions."""
    for col, typ in [
        ("temporary_fingerprint_id", "TEXT"),
        ("temporary_skin_id", "TEXT"),
        ("temporary_turns_remaining", "INTEGER"),
    ]:
        try:
            conn.execute(f"ALTER TABLE chats ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise


def _migrate_v28_entity_tools_social(conn: sqlite3.Connection) -> None:
    """Entity tools, approval_requests, keystore, browser, social, proof_artifacts (Social Media Entity Tools)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tool_definitions (
        tool_id TEXT NOT NULL PRIMARY KEY,
        category TEXT NOT NULL,
        display_name TEXT NOT NULL,
        read_only INTEGER NOT NULL DEFAULT 1,
        requires_approval INTEGER NOT NULL DEFAULT 0,
        requires_browser INTEGER NOT NULL DEFAULT 0,
        requires_network INTEGER NOT NULL DEFAULT 0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS approval_requests (
        approval_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        entity_id TEXT NOT NULL,
        workflow_id TEXT,
        step_id TEXT,
        action_kind TEXT NOT NULL,
        target_platform TEXT,
        target_account_alias TEXT,
        preview_json TEXT NOT NULL,
        status TEXT NOT NULL,
        requested_at TEXT NOT NULL DEFAULT (datetime('now')),
        decided_at TEXT,
        decided_by TEXT,
        decision_note TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_requests_tenant_id ON approval_requests(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_requests_requested_at ON approval_requests(requested_at)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS secret_aliases (
        alias_id TEXT NOT NULL PRIMARY KEY,
        provider_kind TEXT NOT NULL,
        provider_ref TEXT NOT NULL,
        purpose TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        disabled_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS social_accounts (
        social_account_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        platform TEXT NOT NULL,
        account_alias TEXT NOT NULL UNIQUE,
        login_secret_alias_id TEXT,
        mfa_secret_alias_id TEXT,
        entity_scope TEXT,
        persona_scope TEXT,
        state TEXT NOT NULL DEFAULT 'unverified',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_social_accounts_tenant_id ON social_accounts(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS browser_sessions (
        browser_session_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        entity_id TEXT,
        platform TEXT,
        state TEXT NOT NULL,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        ended_at TEXT,
        trace_path TEXT,
        latest_screenshot_path TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_browser_sessions_tenant_id ON browser_sessions(tenant_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS social_actions (
        social_action_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        approval_id TEXT,
        browser_session_id TEXT,
        platform TEXT NOT NULL,
        action_type TEXT NOT NULL,
        target_uri TEXT,
        request_json TEXT NOT NULL,
        result_json TEXT,
        state TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_social_actions_tenant_id ON social_actions(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_social_actions_approval_id ON social_actions(approval_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS proof_artifacts (
        proof_id TEXT NOT NULL PRIMARY KEY,
        related_kind TEXT NOT NULL,
        related_id TEXT NOT NULL,
        artifact_type TEXT NOT NULL,
        path TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proof_artifacts_related ON proof_artifacts(related_kind, related_id)")


def _migrate_v29_chat_persona_state(conn: sqlite3.Connection) -> None:
    """Persona naturalness: session-scoped chat persona state."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chat_persona_state (
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        state_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, chat_id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_persona_state_tenant_id ON chat_persona_state(tenant_id)")


def _migrate_v30_persona_naturalness_analytics(conn: sqlite3.Connection) -> None:
    """Persona naturalness: durable turn analytics and issue rows."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS persona_naturalness_turns (
        turn_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        message_id TEXT,
        fingerprint_id TEXT,
        skin_id TEXT,
        swarm_run_id TEXT,
        swarm_role TEXT,
        input_type TEXT NOT NULL,
        emotional_register TEXT NOT NULL,
        stress_level TEXT NOT NULL,
        chosen_register TEXT NOT NULL,
        chosen_entry_point TEXT NOT NULL,
        tic_count INTEGER NOT NULL DEFAULT 0,
        sample_overlap_score REAL NOT NULL DEFAULT 0,
        recent_overlap_score REAL NOT NULL DEFAULT 0,
        regeneration_attempted INTEGER NOT NULL DEFAULT 0,
        regeneration_succeeded INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS persona_naturalness_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turn_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        issue_code TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_naturalness_turns_tenant_created ON persona_naturalness_turns(tenant_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_naturalness_turns_tenant_chat ON persona_naturalness_turns(tenant_id, chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_naturalness_turns_tenant_swarm ON persona_naturalness_turns(tenant_id, swarm_run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_naturalness_turns_tenant_fingerprint ON persona_naturalness_turns(tenant_id, fingerprint_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_naturalness_issues_turn_id ON persona_naturalness_issues(turn_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_naturalness_issues_tenant_code ON persona_naturalness_issues(tenant_id, issue_code)")


def _migrate_v31_chat_persona_autonomy_state(conn: sqlite3.Connection) -> None:
    """Persona cognitive autonomy: session-scoped temporal autonomy state."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chat_persona_autonomy_state (
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        state_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, chat_id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_persona_autonomy_state_tenant_id ON chat_persona_autonomy_state(tenant_id)")


def _migrate_v32_persona_autonomy_analytics(conn: sqlite3.Connection) -> None:
    """Persona cognitive autonomy: durable turn-level directive telemetry."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS persona_autonomy_turns (
        turn_id TEXT NOT NULL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        message_id TEXT,
        fingerprint_id TEXT,
        skin_id TEXT,
        swarm_run_id TEXT,
        swarm_role TEXT,
        arc_state TEXT NOT NULL,
        engagement_mode TEXT NOT NULL,
        depth_level TEXT NOT NULL,
        uncertainty_level TEXT NOT NULL,
        callback_surface INTEGER NOT NULL DEFAULT 0,
        proactive_notice INTEGER NOT NULL DEFAULT 0,
        lateral_mode TEXT NOT NULL DEFAULT 'skip',
        position_evolution INTEGER NOT NULL DEFAULT 0,
        relationship_type TEXT,
        counterpart_fingerprint_id TEXT,
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_autonomy_turns_tenant_created ON persona_autonomy_turns(tenant_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_autonomy_turns_tenant_chat ON persona_autonomy_turns(tenant_id, chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_autonomy_turns_tenant_swarm ON persona_autonomy_turns(tenant_id, swarm_run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_autonomy_turns_tenant_fingerprint ON persona_autonomy_turns(tenant_id, fingerprint_id)")


def _migrate_v33_run_index(conn: sqlite3.Connection) -> None:
    """Shared run index for operator and realtime paths."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        graph_id TEXT,
        status TEXT,
        started_at REAL,
        ended_at REAL,
        run_dir TEXT,
        correlation_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_correlation_id ON runs(correlation_id)")


def _migrate_v47_runs_blocked_reason(conn: sqlite3.Connection) -> None:
    """Record why a run was blocked (e.g. governance/release gate reason)."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()]
    if "blocked_reason" not in cols:
        conn.execute("ALTER TABLE runs ADD COLUMN blocked_reason TEXT")


def _migrate_v48_runs_pending_request(conn: sqlite3.Connection) -> None:
    """Store RunRequested payload for pending_approval runs so scheduler can launch on approve."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()]
    if "pending_request_json" not in cols:
        conn.execute("ALTER TABLE runs ADD COLUMN pending_request_json TEXT")


def _migrate_v49_human_notifications(conn: sqlite3.Connection) -> None:
    """Shared human notification ledger for operator activity projections."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS human_notifications (
        notification_id TEXT PRIMARY KEY,
        recorded_at TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        task_name TEXT NOT NULL,
        channel TEXT NOT NULL,
        recipient TEXT NOT NULL,
        kind TEXT NOT NULL,
        transport TEXT NOT NULL,
        message TEXT NOT NULL,
        summary_json TEXT NOT NULL,
        social_account_id TEXT,
        tenant_id TEXT,
        operational_agent_id TEXT,
        payload_json TEXT NOT NULL
        )"""
    )
    cols = [row[1] for row in conn.execute("PRAGMA table_info(human_notifications)").fetchall()]
    if "recorded_at" not in cols:
        conn.execute("ALTER TABLE human_notifications ADD COLUMN recorded_at TEXT")
        conn.execute("UPDATE human_notifications SET recorded_at = timestamp WHERE recorded_at IS NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_human_notifications_timestamp ON human_notifications(timestamp DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_human_notifications_recorded ON human_notifications(recorded_at DESC, timestamp DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_human_notifications_task ON human_notifications(task_name, recorded_at DESC, timestamp DESC)")


def _migrate_v50_commitment_records(conn: sqlite3.Connection) -> None:
    """Shared commitment/promise ledger for runtime and operator projections."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS commitment_records (
        commitment_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        operational_agent_id TEXT,
        entity_id TEXT,
        commitment_kind TEXT NOT NULL DEFAULT 'promise',
        title TEXT NOT NULL,
        details_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL,
        due_at TEXT,
        fulfilled_at TEXT,
        expired_at TEXT,
        resolution_note TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_commitment_records_tenant_task ON commitment_records(tenant_id, task_name, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_commitment_records_tenant_agent ON commitment_records(tenant_id, operational_agent_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_commitment_records_tenant_entity ON commitment_records(tenant_id, entity_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_commitment_records_status_due ON commitment_records(status, due_at, created_at DESC)")


def _migrate_v51_content_documents(conn: sqlite3.Connection) -> None:
    """Editable markdown content registry and version ledger."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS content_document_classes (
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
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS content_documents (
        content_id TEXT PRIMARY KEY,
        class_key TEXT NOT NULL,
        file_path TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        current_version_id TEXT,
        source_sha256 TEXT NOT NULL,
        source_size_bytes INTEGER NOT NULL,
        source_mtime TEXT,
        editable INTEGER NOT NULL DEFAULT 1,
        archived INTEGER NOT NULL DEFAULT 0,
        latest_status TEXT NOT NULL DEFAULT 'discovered',
        imported_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_documents_class ON content_documents(class_key, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_documents_status ON content_documents(latest_status, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS content_document_versions (
        version_id TEXT PRIMARY KEY,
        content_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'imported',
        content_markdown TEXT NOT NULL,
        content_sha256 TEXT NOT NULL,
        source_path TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        author_id TEXT,
        change_summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        UNIQUE(content_id, version_number)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_document_versions_content ON content_document_versions(content_id, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_document_versions_created ON content_document_versions(created_at DESC)")
    content_classes = [
        (
            "task",
            "Automation task files",
            "skills/automation/tasks",
            "**/*.md",
            "Operator task instructions executed by the automation runtime and job registry.",
            '{"editable":"yes","versioning":"required","source":"skills/automation/tasks"}',
        ),
        (
            "skill",
            "Automation skill docs",
            "skills/automation",
            "**/*.md",
            "Skill and runbook docs that shape automation behavior and operator guidance.",
            '{"editable":"yes","versioning":"required","source":"skills/automation"}',
        ),
        (
            "plan",
            "Plan docs",
            ".cursor/plans",
            "**/*.md",
            "Execution plans, tranche specs, and roadmap docs that operators edit in-browser.",
            '{"editable":"yes","versioning":"required","source":".cursor/plans"}',
        ),
        (
            "runbook",
            "Runbooks",
            "docs/runbooks",
            "**/*.md",
            "Operational and support runbooks that should be editable without leaving the browser.",
            '{"editable":"yes","versioning":"required","source":"docs/runbooks"}',
        ),
    ]
    for class_key, title, root_path, glob_pattern, description, metadata_json in content_classes:
        conn.execute(
            """
            INSERT OR IGNORE INTO content_document_classes (
                class_key, title, root_path, glob_pattern, description,
                editable, versioned, import_required, archive_policy,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 1, 1, 'archive-on-supersede', ?, datetime('now'), datetime('now'))
            """,
            (class_key, title, root_path, glob_pattern, description, metadata_json),
        )


def _migrate_v52_tool_registry(conn: sqlite3.Connection) -> None:
    """Script/tool registry metadata and version ledger."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tool_registry_entries (
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
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_registry_entries_kind ON tool_registry_entries(tool_kind, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_registry_entries_platform ON tool_registry_entries(platform_id, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tool_registry_versions (
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
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_registry_versions_tool ON tool_registry_versions(tool_id, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_registry_versions_created ON tool_registry_versions(created_at DESC)")


def _migrate_v53_artifact_registry(conn: sqlite3.Connection) -> None:
    """Generated artifact, log, screenshot, backup, and snapshot registry."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS artifact_registry_classes (
        class_key TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        root_path TEXT NOT NULL,
        glob_pattern TEXT NOT NULL,
        description TEXT NOT NULL,
        editable INTEGER NOT NULL DEFAULT 0,
        versioned INTEGER NOT NULL DEFAULT 1,
        import_required INTEGER NOT NULL DEFAULT 1,
        archive_policy TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS artifact_registry_entries (
        artifact_id TEXT PRIMARY KEY,
        class_key TEXT NOT NULL,
        file_path TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        source_size_bytes INTEGER NOT NULL,
        source_mtime TEXT,
        content_kind TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        current_version_id TEXT,
        latest_status TEXT NOT NULL DEFAULT 'current',
        active INTEGER NOT NULL DEFAULT 1,
        imported_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_registry_entries_class ON artifact_registry_entries(class_key, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_registry_entries_status ON artifact_registry_entries(latest_status, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_registry_entries_active ON artifact_registry_entries(active, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS artifact_registry_versions (
        version_id TEXT PRIMARY KEY,
        artifact_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'imported',
        file_path TEXT NOT NULL,
        class_key TEXT NOT NULL,
        content_kind TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        source_size_bytes INTEGER NOT NULL,
        source_mtime TEXT,
        author_id TEXT,
        change_summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        UNIQUE(artifact_id, version_number)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_registry_versions_artifact ON artifact_registry_versions(artifact_id, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifact_registry_versions_created ON artifact_registry_versions(created_at DESC)")


def _migrate_v54_task_registry(conn: sqlite3.Connection) -> None:
    """Task executable registry metadata and version ledger."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS task_registry_entries (
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
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_entries_platform ON task_registry_entries(platform_id, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_entries_mode ON task_registry_entries(mode, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_entries_session_target ON task_registry_entries(session_target, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS task_registry_versions (
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
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_versions_task ON task_registry_versions(task_name, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_registry_versions_created ON task_registry_versions(created_at DESC)")


def _migrate_v55_source_blob_registry(conn: sqlite3.Connection) -> None:
    """Python source blob registry metadata and version ledger."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS source_blob_classes (
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
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS source_blob_entries (
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
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_entries_class ON source_blob_entries(class_key, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_entries_status ON source_blob_entries(latest_status, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS source_blob_versions (
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
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_versions_blob ON source_blob_versions(source_blob_id, version_number DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_blob_versions_created ON source_blob_versions(created_at DESC)")
    conn.execute(
        """INSERT OR IGNORE INTO source_blob_classes (
        class_key, title, root_path, glob_pattern, description,
        editable, versioned, import_required, archive_policy,
        metadata_json, created_at, updated_at
        ) VALUES (
        'python_source', 'Python source blobs', 'hg_platforms', '**/*.py',
        'Executable Python source modules for live platform integrations and runtime entrypoints.',
        1, 1, 1, 'archive-on-supersede',
        '{"editable":"yes","versioning":"required","source":"hg_platforms"}',
        datetime('now'), datetime('now')
        )"""
    )


def _migrate_v34_l10_events(conn: sqlite3.Connection) -> None:
    """Operator L10 events in the shared gateway database."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS l10_events (
        event_id TEXT PRIMARY KEY,
        correlation_id TEXT,
        run_id TEXT,
        tenant_id TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at REAL NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_l10_events_correlation ON l10_events(correlation_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_l10_events_run ON l10_events(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_l10_events_created ON l10_events(created_at)")


def _migrate_v35_run_leases(conn: sqlite3.Connection) -> None:
    """Shared run leases for realtime worker and operator lifecycle."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS run_leases (
        run_id TEXT PRIMARY KEY,
        lease_id TEXT NOT NULL,
        worker_id TEXT NOT NULL,
        acquired_at REAL NOT NULL,
        last_heartbeat_at REAL NOT NULL,
        seq INTEGER NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_leases_worker_id ON run_leases(worker_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_leases_last_heartbeat ON run_leases(last_heartbeat_at)")


def _migrate_v36_persona_catalog(conn: sqlite3.Connection) -> None:
    """Shared persona catalog for operator and gateway-backed persona selection."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS persona_catalog (
        source TEXT NOT NULL,
        persona_id TEXT NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        path TEXT NOT NULL,
        is_skin INTEGER NOT NULL DEFAULT 0,
        base_profile TEXT,
        sha256 TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (source, persona_id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persona_catalog_source_skin ON persona_catalog(source, is_skin)")


def _migrate_v37_steering_store(conn: sqlite3.Connection) -> None:
    """Shared steering command store for operator and realtime control."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS steering_events (
        steering_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        node_id TEXT,
        kind TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        consumed INTEGER NOT NULL DEFAULT 0
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_steering_run_id ON steering_events(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_steering_run_consumed ON steering_events(run_id, consumed)")


def _migrate_v38_knowledge_documents(conn: sqlite3.Connection) -> None:
    """Shared knowledge metadata/content mirror for operator-visible search and stats."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS knowledge_documents (
        file_path TEXT PRIMARY KEY,
        title TEXT,
        category TEXT,
        language TEXT,
        content TEXT NOT NULL,
        word_count INTEGER,
        last_indexed TEXT,
        file_hash TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_category ON knowledge_documents(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_language ON knowledge_documents(language)")


def _migrate_v39_memory_graphs(conn: sqlite3.Connection) -> None:
    """Shared agent memory documents and per-agent entity graph."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_agent_documents (
        agent_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        content TEXT NOT NULL,
        date TEXT,
        language TEXT,
        metadata TEXT NOT NULL,
        word_count INTEGER,
        last_indexed TEXT,
        file_hash TEXT,
        source_type TEXT,
        content_normalized TEXT,
        PRIMARY KEY (agent_id, file_path)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_agent_documents_agent_date ON memory_agent_documents(agent_id, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_agent_documents_agent_source ON memory_agent_documents(agent_id, source_type)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        path TEXT NOT NULL,
        summary_excerpt TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(agent_id, type, name)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_entities_agent ON memory_entities(agent_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        fact TEXT NOT NULL,
        category TEXT,
        timestamp TEXT,
        source TEXT,
        status TEXT,
        related_entities_json TEXT,
        last_accessed_at TEXT,
        FOREIGN KEY (entity_id) REFERENCES memory_entities(id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_facts_agent ON memory_facts(agent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_facts_entity ON memory_facts(entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_facts_timestamp ON memory_facts(timestamp)")


def _migrate_v40_memory_context_identity(conn: sqlite3.Connection) -> None:
    """Shared context and identity graph tables."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_context_entities (
        entity_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        agent_id TEXT,
        timestamp TEXT NOT NULL,
        properties TEXT,
        content TEXT NOT NULL,
        language TEXT,
        content_normalized TEXT,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_context_entities_agent ON memory_context_entities(agent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_context_entities_type ON memory_context_entities(entity_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_context_entities_timestamp ON memory_context_entities(timestamp)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_context_relations (
        relation_id TEXT PRIMARY KEY,
        from_entity_id TEXT NOT NULL,
        to_entity_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        timestamp TEXT,
        properties TEXT,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_context_relations_from ON memory_context_relations(from_entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_context_relations_to ON memory_context_relations(to_entity_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_identity_entities (
        entity_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        agent_id TEXT,
        platform TEXT,
        timestamp TEXT NOT NULL,
        properties TEXT,
        content TEXT NOT NULL,
        language TEXT,
        content_normalized TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        deleted_at TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_identity_entities_agent ON memory_identity_entities(agent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_identity_entities_platform ON memory_identity_entities(platform)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_identity_entities_type ON memory_identity_entities(entity_type)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_identity_relations (
        relation_id TEXT PRIMARY KEY,
        from_entity_id TEXT NOT NULL,
        to_entity_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        timestamp TEXT,
        properties TEXT,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_identity_versions (
        version_id TEXT PRIMARY KEY,
        persona_file TEXT NOT NULL,
        platform TEXT,
        persona_set TEXT,
        agent_id TEXT,
        timestamp TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        diff_before TEXT,
        diff_after TEXT,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_identity_patterns (
        pattern_id TEXT PRIMARY KEY,
        pattern_type TEXT NOT NULL,
        agent_id TEXT,
        platform TEXT,
        timestamp TEXT NOT NULL,
        properties TEXT,
        created_at TEXT NOT NULL
        )"""
    )


def _migrate_v41_operational_history(conn: sqlite3.Connection) -> None:
    """Operational history replacing overseer JSONL feeds."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS overseer_timeseries (
        event_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        payload TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_overseer_timeseries_timestamp ON overseer_timeseries(timestamp)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS overseer_latest_state (
        slot TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS meditation_reports (
        report_id TEXT PRIMARY KEY,
        actor_id TEXT,
        window_end_ts TEXT,
        created_at TEXT NOT NULL,
        payload TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_meditation_reports_actor ON meditation_reports(actor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_meditation_reports_window_end ON meditation_reports(window_end_ts)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS audit_entries (
        entry_id TEXT PRIMARY KEY,
        role TEXT,
        action TEXT NOT NULL,
        resource_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        details TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_entries_timestamp ON audit_entries(timestamp)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS approval_overrides (
        override_id TEXT PRIMARY KEY,
        approval_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        role TEXT,
        timestamp TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_overrides_approval ON approval_overrides(approval_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS steering_telemetry (
        event_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        event_name TEXT NOT NULL,
        payload TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_steering_telemetry_timestamp ON steering_telemetry(timestamp)")


def _migrate_v42_agent_decisions(conn: sqlite3.Connection) -> None:
    """Structured agent decisions replacing per-agent decisions.json reads."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS agent_decisions (
        decision_id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        rationale TEXT NOT NULL,
        alternatives TEXT NOT NULL,
        tradeoffs TEXT,
        context TEXT,
        outcome TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_decisions_agent_timestamp ON agent_decisions(agent_id, timestamp)")


def _migrate_v45_governance_spine(conn: sqlite3.Connection) -> None:
    """Canonical gate / receipts / policies / constitutional memory tables."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sealed_receipts (
        receipt_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        receipt_kind TEXT NOT NULL,
        subject_kind TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        run_id TEXT,
        chat_id TEXT,
        turn_id TEXT,
        tool_call_id TEXT,
        approval_id TEXT,
        policy_key TEXT,
        policy_version_id TEXT,
        gate_family TEXT,
        constitutional_root_id TEXT,
        canonical_json TEXT NOT NULL,
        canonical_sha256 TEXT NOT NULL,
        prev_receipt_sha256 TEXT,
        receipt_sha256 TEXT NOT NULL,
        seal_algorithm TEXT NOT NULL,
        seal_key_id TEXT,
        verification_status TEXT NOT NULL DEFAULT 'verified',
        event_id TEXT,
        ledger_id TEXT,
        supersedes_receipt_id TEXT,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sealed_receipts_tenant_created ON sealed_receipts(tenant_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sealed_receipts_subject ON sealed_receipts(subject_kind, subject_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sealed_receipts_policy ON sealed_receipts(policy_key, policy_version_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS policy_registry (
        policy_key TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        current_version_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS policy_versions (
        version_id TEXT PRIMARY KEY,
        policy_key TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        state TEXT NOT NULL,
        rationale TEXT,
        change_summary TEXT,
        content_json TEXT NOT NULL,
        diff_json TEXT,
        simulation_summary_json TEXT,
        effect_metrics_json TEXT,
        created_at TEXT NOT NULL,
        activated_at TEXT,
        superseded_at TEXT,
        receipt_id TEXT,
        UNIQUE(policy_key, version_number)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_versions_key_state ON policy_versions(policy_key, state)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS policy_feedback (
        feedback_id TEXT PRIMARY KEY,
        policy_version_id TEXT NOT NULL,
        author_id TEXT,
        sentiment TEXT,
        summary TEXT NOT NULL,
        details_json TEXT,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_feedback_version ON policy_feedback(policy_version_id, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS policy_simulations (
        simulation_id TEXT PRIMARY KEY,
        policy_version_id TEXT NOT NULL,
        scenario_label TEXT NOT NULL,
        inputs_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        receipt_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_simulations_version ON policy_simulations(policy_version_id, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS constitutional_roots (
        root_id TEXT PRIMARY KEY,
        workflow_family TEXT NOT NULL,
        title TEXT NOT NULL,
        root_goal TEXT NOT NULL,
        owner_id TEXT,
        accountable_actor TEXT,
        material_constraints_json TEXT NOT NULL,
        approved_subgoals_json TEXT NOT NULL,
        policy_version_id TEXT,
        status TEXT NOT NULL,
        drift_severity TEXT NOT NULL DEFAULT 'stable',
        last_checkpoint_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_constitutional_roots_workflow ON constitutional_roots(workflow_family, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS constitutional_checkpoints (
        checkpoint_id TEXT PRIMARY KEY,
        root_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        alignment_score REAL,
        state_json TEXT NOT NULL,
        actor_id TEXT,
        created_at TEXT NOT NULL,
        receipt_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_constitutional_checkpoints_root ON constitutional_checkpoints(root_id, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS constitutional_drift_events (
        drift_event_id TEXT PRIMARY KEY,
        root_id TEXT NOT NULL,
        severity TEXT NOT NULL,
        summary TEXT NOT NULL,
        details_json TEXT NOT NULL,
        acknowledged_at TEXT,
        acknowledged_by TEXT,
        override_status TEXT,
        created_at TEXT NOT NULL,
        receipt_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_constitutional_drift_root ON constitutional_drift_events(root_id, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gate_benchmark_sets (
        benchmark_set_id TEXT PRIMARY KEY,
        workflow_family TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        weights_json TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gate_benchmark_sets_workflow ON gate_benchmark_sets(workflow_family, active, updated_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gate_benchmark_runs (
        benchmark_run_id TEXT PRIMARY KEY,
        benchmark_set_id TEXT NOT NULL,
        workflow_family TEXT NOT NULL,
        candidate_label TEXT NOT NULL,
        observations_json TEXT NOT NULL,
        actor_id TEXT,
        created_at TEXT NOT NULL,
        receipt_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gate_benchmark_runs_set ON gate_benchmark_runs(benchmark_set_id, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gate_evaluations (
        evaluation_id TEXT PRIMARY KEY,
        benchmark_run_id TEXT NOT NULL,
        workflow_family TEXT NOT NULL,
        policy_version_id TEXT,
        p_h REAL NOT NULL,
        p_ai REAL NOT NULL,
        p_h_odei REAL NOT NULL,
        sigma REAL NOT NULL,
        weighted_score REAL NOT NULL,
        verdict TEXT NOT NULL,
        breakdown_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        receipt_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gate_evaluations_workflow ON gate_evaluations(workflow_family, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gate_release_verdicts (
        release_verdict_id TEXT PRIMARY KEY,
        workflow_family TEXT NOT NULL,
        target_kind TEXT NOT NULL,
        target_id TEXT NOT NULL,
        environment TEXT NOT NULL,
        evaluation_id TEXT,
        verdict TEXT NOT NULL,
        reason TEXT,
        stale_after_ts TEXT,
        created_at TEXT NOT NULL,
        receipt_id TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gate_release_verdicts_target ON gate_release_verdicts(workflow_family, target_kind, target_id, created_at DESC)")


def _migrate_v46_governed_research_surface(conn: sqlite3.Connection) -> None:
    """Governed research/document surface and scheduler request deconfliction."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS research_runs (
        research_run_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        workspace_kind TEXT NOT NULL,
        source_message_id TEXT,
        title TEXT NOT NULL,
        query_text TEXT,
        document_id TEXT,
        plan_template TEXT,
        assistant_message_id TEXT,
        assistant_excerpt TEXT,
        provenance_json TEXT NOT NULL,
        policy_version_id TEXT,
        constitutional_root_id TEXT,
        receipt_id TEXT,
        synced_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_tenant_created ON research_runs(tenant_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_chat_created ON research_runs(chat_id, created_at DESC)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS research_decomposition_nodes (
        node_id TEXT PRIMARY KEY,
        research_run_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        label TEXT NOT NULL,
        summary TEXT,
        depth INTEGER NOT NULL DEFAULT 0,
        source_document_id TEXT,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_decomposition_run ON research_decomposition_nodes(research_run_id, depth, created_at)")
