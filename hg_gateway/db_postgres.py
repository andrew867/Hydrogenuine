"""
Postgres connection and schema bootstrap for gateway persistence.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Mapping, Optional, Sequence

import psycopg
from psycopg.errors import DuplicateObject, UniqueViolation

from hg_gateway.db import (
    SCHEMA_VERSION,
    _migrate,
    _migrate_v23_approval_policy,
    _migrate_v43_approval_rules,
    _migrate_v47_runs_blocked_reason,
    _migrate_v48_runs_pending_request,
)
from hg_gateway.storage_config import gateway_postgres_dsn

_BOOTSTRAPPED_DSNS: set[str] = set()
_BOOTSTRAP_LOCK = threading.Lock()

_REPLACE_CONFLICT_TARGETS = {
    "approval_chat_lock": ["approval_id"],
    "chat_traits": ["tenant_id", "chat_id"],
    "chat_persona_state": ["tenant_id", "chat_id"],
    "chat_persona_autonomy_state": ["tenant_id", "chat_id"],
    "runs": ["run_id"],
    "stepup_secrets": ["user_id"],
    "persona_catalog": ["source", "persona_id"],
    "persona_naturalness_turns": ["turn_id"],
    "persona_autonomy_turns": ["turn_id"],
    "steering_events": ["steering_id"],
    "human_notifications": ["notification_id"],
    "commitment_records": ["commitment_id"],
    "knowledge_documents": ["file_path"],
    "memory_agent_documents": ["agent_id", "file_path"],
    "memory_entities": ["agent_id", "type", "name"],
    "memory_context_entities": ["entity_id"],
    "memory_context_relations": ["relation_id"],
    "memory_identity_entities": ["entity_id"],
    "memory_identity_relations": ["relation_id"],
    "memory_identity_versions": ["version_id"],
    "memory_identity_patterns": ["pattern_id"],
    "overseer_timeseries": ["event_id"],
    "overseer_latest_state": ["slot"],
    "meditation_reports": ["report_id"],
    "operational_state": ["state_key"],
    "agent_decisions": ["decision_id"],
    "policy_registry": ["policy_key"],
    "constitutional_roots": ["root_id"],
    "research_runs": ["research_run_id"],
    "research_decomposition_nodes": ["node_id"],
}

# Tables with integer identity (BIGSERIAL) that get sequence sync on bootstrap and on UniqueViolation retry.
IDENTITY_COLUMNS: list[tuple[str, str]] = [
    ("events", "event_id"),
    ("probe_results", "id"),
    ("audit_events", "event_id"),
    ("signal_features", "id"),
    ("persona_naturalness_issues", "id"),
    ("memory_entities", "id"),
    ("memory_facts", "id"),
]
_CONSTRAINT_TO_IDENTITY: dict[str, tuple[str, str]] = {
    f"{table}_pkey": (table, column) for table, column in IDENTITY_COLUMNS
}


class RowCompat(dict):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class PostgresCompatCursor:
    def __init__(self, cursor: psycopg.Cursor[Any]) -> None:
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def _wrap_row(self, row: Any) -> Any:
        if row is None:
            return None
        if isinstance(row, dict):
            return RowCompat(row)
        if self._cursor.description:
            keys = [item.name for item in self._cursor.description]
            return RowCompat({key: value for key, value in zip(keys, row)})
        return row

    def fetchone(self) -> Any:
        return self._wrap_row(self._cursor.fetchone())

    def fetchall(self) -> list[Any]:
        return [self._wrap_row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield self._wrap_row(row)

    def close(self) -> None:
        self._cursor.close()


class PostgresCompatConnection:
    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Optional[Any] = None) -> PostgresCompatCursor:
        translated_sql = _translate_runtime_sql(sql)
        params_norm = _normalize_params(params)
        _SAVEPOINT = "before_identity_exec"
        with self._conn.cursor() as sp_cur:
            sp_cur.execute(f"SAVEPOINT {_SAVEPOINT}")
        cur = self._conn.cursor()
        try:
            cur.execute(translated_sql, params_norm)
            return PostgresCompatCursor(cur)
        except UniqueViolation as ex:
            constraint_name = getattr(getattr(ex, "diag", None), "constraint_name", None)
            if constraint_name not in _CONSTRAINT_TO_IDENTITY:
                raise
            table, column = _CONSTRAINT_TO_IDENTITY[constraint_name]
            cur.close()
            with self._conn.cursor() as rb_cur:
                rb_cur.execute(f"ROLLBACK TO SAVEPOINT {_SAVEPOINT}")
            _sync_sequence_for_identity(self._conn, table, column)
            cur2 = self._conn.cursor()
            cur2.execute(translated_sql, params_norm)
            return PostgresCompatCursor(cur2)

    def executemany(self, sql: str, seq_of_params: Sequence[Any]) -> PostgresCompatCursor:
        translated_sql = _translate_runtime_sql(sql)
        params_list = [_normalize_params(params) for params in seq_of_params]
        _SAVEPOINT = "before_identity_execmany"
        with self._conn.cursor() as sp_cur:
            sp_cur.execute(f"SAVEPOINT {_SAVEPOINT}")
        cur = self._conn.cursor()
        try:
            cur.executemany(translated_sql, params_list)
            return PostgresCompatCursor(cur)
        except UniqueViolation as ex:
            constraint_name = getattr(getattr(ex, "diag", None), "constraint_name", None)
            if constraint_name not in _CONSTRAINT_TO_IDENTITY:
                raise
            table, column = _CONSTRAINT_TO_IDENTITY[constraint_name]
            cur.close()
            with self._conn.cursor() as rb_cur:
                rb_cur.execute(f"ROLLBACK TO SAVEPOINT {_SAVEPOINT}")
            _sync_sequence_for_identity(self._conn, table, column)
            cur2 = self._conn.cursor()
            cur2.executemany(translated_sql, params_list)
            return PostgresCompatCursor(cur2)

    def executescript(self, script: str) -> None:
        for statement in _split_sql_statements(script):
            if statement.strip():
                self.execute(statement)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def _postgres_dsn() -> str:
    return gateway_postgres_dsn(required=True)


def _translate_placeholders(sql: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    idx = 0
    while idx < len(sql):
        char = sql[idx]
        if char == "'" and not in_double:
            in_single = not in_single
            out.append(char)
        elif char == '"' and not in_single:
            in_double = not in_double
            out.append(char)
        elif char == "?" and not in_single and not in_double:
            out.append("%s")
        elif char == ":" and not in_single and not in_double:
            prev_char = sql[idx - 1] if idx > 0 else ""
            if prev_char == ":":
                out.append(char)
            else:
                match = re.match(r":([A-Za-z_][A-Za-z0-9_]*)", sql[idx:])
                if match:
                    key = match.group(1)
                    out.append(f"%({key})s")
                    idx += len(match.group(0)) - 1
                else:
                    out.append(char)
        else:
            out.append(char)
        idx += 1
    return "".join(out)


def _normalize_params(params: Optional[Any]) -> Any:
    if params is None:
        return ()
    if isinstance(params, Mapping):
        return dict(params)
    if isinstance(params, (str, bytes)):
        return (params,)
    return tuple(params)


def _translate_insert_or_ignore(sql: str) -> str:
    return re.sub(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", "INSERT INTO ", sql, flags=re.IGNORECASE) + " ON CONFLICT DO NOTHING"


def _translate_insert_or_replace(sql: str) -> str:
    match = re.match(
        r"^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+([A-Za-z0-9_\"']+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*$",
        sql.strip(),
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Unsupported INSERT OR REPLACE statement for Postgres: {sql}")
    table = match.group(1).strip("\"'")
    raw_columns = match.group(2)
    raw_values = match.group(3)
    columns = [part.strip().strip("\"'") for part in raw_columns.split(",")]
    conflict_cols = _REPLACE_CONFLICT_TARGETS.get(table)
    if not conflict_cols:
        raise RuntimeError(f"Missing Postgres conflict target mapping for table '{table}'")
    update_cols = [col for col in columns if col not in conflict_cols]
    assignments = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols) or ", ".join(
        f"{col} = {table}.{col}" for col in conflict_cols
    )
    return (
        f"INSERT INTO {table} ({raw_columns}) VALUES ({raw_values}) "
        f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {assignments}"
    )


def _translate_sqlite_master_query(sql: str) -> Optional[str]:
    normalized = " ".join(sql.strip().split()).lower()
    if "from sqlite_master" not in normalized:
        return None
    if "type='table'" in normalized:
        return "SELECT tablename AS name FROM pg_tables WHERE schemaname = current_schema()"
    if "type='index'" in normalized:
        return "SELECT indexname AS name FROM pg_indexes WHERE schemaname = current_schema()"
    return "SELECT tablename AS name FROM pg_tables WHERE schemaname = current_schema()"


def _translate_pragma_table_info(sql: str) -> Optional[str]:
    match = re.match(r"^\s*PRAGMA\s+table_info\(([^)]+)\)\s*$", sql.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    table = match.group(1).strip().strip("'\"")
    return f"""
        SELECT
            ordinal_position - 1 AS cid,
            column_name AS name,
            data_type AS type,
            CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
            column_default AS dflt_value,
            CASE WHEN column_name IN (
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = '{table}'::regclass AND i.indisprimary
            ) THEN 1 ELSE 0 END AS pk
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = '{table}'
        ORDER BY ordinal_position
    """


def _translate_runtime_sql(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    pragma = _translate_pragma_table_info(stripped)
    if pragma:
        return pragma
    sqlite_master = _translate_sqlite_master_query(stripped)
    if sqlite_master:
        return sqlite_master
    translated = stripped.replace("datetime('now')", "CURRENT_TIMESTAMP")
    if re.match(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", translated, flags=re.IGNORECASE):
        translated = _translate_insert_or_ignore(translated)
    elif re.match(r"^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+", translated, flags=re.IGNORECASE):
        translated = _translate_insert_or_replace(translated)
    translated = _translate_placeholders(translated)
    return translated


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    buff: list[str] = []
    in_single = False
    in_double = False
    for char in script:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            stmt = "".join(buff).strip()
            if stmt:
                statements.append(stmt)
            buff = []
            continue
        buff.append(char)
    tail = "".join(buff).strip()
    if tail:
        statements.append(tail)
    return statements


def _translate_create_statement(sql: str) -> Optional[str]:
    statement = sql.strip()
    if "VIRTUAL TABLE" in statement.upper():
        return None
    statement = re.sub(r"^CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", statement, flags=re.IGNORECASE)
    statement = re.sub(r"^CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", statement, flags=re.IGNORECASE)
    statement = re.sub(r"^CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", statement, flags=re.IGNORECASE)
    statement = statement.replace("AUTOINCREMENT", "")
    statement = re.sub(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "BIGSERIAL PRIMARY KEY", statement, flags=re.IGNORECASE)
    statement = statement.replace(" BLOB", " BYTEA")
    statement = statement.replace("(datetime('now'))", "CURRENT_TIMESTAMP")
    statement = statement.replace("datetime('now')", "CURRENT_TIMESTAMP")
    statement = statement.replace(" WITHOUT ROWID", "")
    return statement


def _render_postgres_schema_statements() -> list[str]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    statements = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    ]
    rows = conn.execute(
        "SELECT type, name, sql, rowid FROM sqlite_master WHERE sql IS NOT NULL ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, rowid"
    ).fetchall()
    for row in rows:
        name = str(row["name"])
        if name.startswith("sqlite_") or name.startswith("signal_events_fts"):
            continue
        translated = _translate_create_statement(str(row["sql"]))
        if translated:
            statements.append(translated)
    statements.append(
        f"INSERT INTO _schema_version (version, applied_at) VALUES ({SCHEMA_VERSION}, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"
    )
    conn.close()
    return statements


def _sync_sequence_for_identity(conn: psycopg.Connection[Any], table: str, column: str) -> None:
    """Set sequence to MAX(column)+1 so next nextval does not collide. Used on UniqueViolation retry."""
    sequence_name = f"{table}_{column}_seq"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT setval(
            '{sequence_name}'::regclass,
            COALESCE((SELECT MAX("{column}") FROM "{table}"), 0) + 1,
            false
        )
        """
    )
    cur.close()


def _ensure_integer_identity_defaults(conn: psycopg.Connection[Any]) -> None:
    for table, column in IDENTITY_COLUMNS:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            continue
        default = row[0]
        sequence_name = f"{table}_{column}_seq"
        if default and "nextval(" in str(default):
            # Column already has sequence default; re-sync sequence so next value is > MAX(column).
            cur.close()
            try:
                _sync_sequence_for_identity(conn, table, column)
            except Exception:
                conn.rollback()
            continue
        try:
            cur.execute(f'CREATE SEQUENCE IF NOT EXISTS "{sequence_name}"')
        except (DuplicateObject, UniqueViolation):
            conn.rollback()
            cur = conn.cursor()
        _sync_sequence_for_identity(conn, table, column)
        cur.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT nextval(\'{sequence_name}\')'
        )
        cur.execute(
            f'ALTER SEQUENCE "{sequence_name}" OWNED BY "{table}"."{column}"'
        )
        cur.close()


def ensure_postgres_schema(dsn: Optional[str] = None) -> None:
    resolved_dsn = dsn or _postgres_dsn()
    if resolved_dsn in _BOOTSTRAPPED_DSNS:
        return
    with _BOOTSTRAP_LOCK:
        if resolved_dsn in _BOOTSTRAPPED_DSNS:
            return
        with psycopg.connect(resolved_dsn) as conn:
            cur = conn.cursor()
            for statement in _render_postgres_schema_statements():
                try:
                    cur.execute(statement)
                except (DuplicateObject, UniqueViolation):
                    if statement.startswith("CREATE EXTENSION IF NOT EXISTS "):
                        conn.rollback()
                        continue
                    raise
            compat = PostgresCompatConnection(conn)
            # Run the SQLite migration chain through the compat layer so existing
            # Postgres schemas pick up later ALTER-based changes too.
            _migrate(compat)
            # Some additive columns live behind version-gated SQLite migrations.
            # Existing Postgres schemas can already report the latest version while
            # still missing these later columns, so enforce the idempotent alters.
            _migrate_v23_approval_policy(compat)
            _migrate_v43_approval_rules(compat)
            _migrate_v47_runs_blocked_reason(compat)
            _migrate_v48_runs_pending_request(compat)
            _ensure_integer_identity_defaults(conn)
            conn.commit()
        _BOOTSTRAPPED_DSNS.add(resolved_dsn)


def reset_postgres_bootstrap_cache(dsn: Optional[str] = None) -> None:
    resolved_dsn = dsn or _postgres_dsn()
    with _BOOTSTRAP_LOCK:
        _BOOTSTRAPPED_DSNS.discard(resolved_dsn)


@contextmanager
def get_postgres_connection() -> Generator[PostgresCompatConnection, None, None]:
    dsn = _postgres_dsn()
    ensure_postgres_schema(dsn)
    conn = psycopg.connect(dsn)
    try:
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
        yield PostgresCompatConnection(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
