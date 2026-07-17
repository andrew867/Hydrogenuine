"""Structured Data Store backed by Postgres with migration ledger."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg

from hg_core.storage_substrate.common import SCHEMA_VERSION, authority_fields, require_non_authority, stable_hash, stable_json, utc_now_iso

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS storage_schema_versions (
    schema_name text PRIMARY KEY,
    schema_version text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS storage_migration_ledger (
    migration_id text PRIMARY KEY,
    from_version text,
    to_version text NOT NULL,
    applied boolean NOT NULL DEFAULT false,
    dry_run boolean NOT NULL DEFAULT true,
    sql_digest text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS append_log_entries (
    id bigserial PRIMARY KEY,
    stream_id text NOT NULL,
    seq integer NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(stream_id, seq)
);

CREATE TABLE IF NOT EXISTS proof_artifacts (
    artifact_id text PRIMARY KEY,
    artifact_path text NOT NULL,
    artifact_hash text NOT NULL,
    command_log_present boolean NOT NULL DEFAULT false,
    gate_name text,
    verdict text,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS structured_state_records (
    record_id text PRIMARY KEY,
    record_type text NOT NULL,
    payload jsonb NOT NULL,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vector_memory_records (
    record_id text PRIMARY KEY,
    namespace text NOT NULL DEFAULT 'default',
    source_ref text NOT NULL,
    model_id text NOT NULL,
    provider text NOT NULL DEFAULT 'deterministic_fixture',
    dimension integer NOT NULL,
    embedding vector(4) NOT NULL,
    payload jsonb NOT NULL,
    retention_class text NOT NULL,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS blob_artifacts (
    artifact_id text PRIMARY KEY,
    artifact_path text NOT NULL,
    artifact_hash text NOT NULL,
    artifact_class text NOT NULL DEFAULT 'UNKNOWN_REVIEW_REQUIRED',
    mime_type text NOT NULL,
    size_bytes bigint NOT NULL,
    retention_class text NOT NULL,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS retention_plans (
    plan_id text PRIMARY KEY,
    target_ref text NOT NULL,
    retention_class text NOT NULL,
    dry_run boolean NOT NULL DEFAULT true,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backup_manifests (
    manifest_id text PRIMARY KEY,
    payload jsonb NOT NULL,
    schema_version text NOT NULL,
    restore_authority_created boolean NOT NULL DEFAULT false,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS storage_receipts (
    receipt_id text PRIMARY KEY,
    receipt_type text NOT NULL,
    subsystem text NOT NULL,
    payload jsonb NOT NULL,
    permission_granted boolean NOT NULL DEFAULT false,
    authority_created boolean NOT NULL DEFAULT false,
    advisory_only boolean NOT NULL DEFAULT true,
    hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
"""


def default_dsn() -> str:
    return os.environ.get("HG_STORAGE_POSTGRES_DSN", "postgresql://hydrogenuine:hydrogenuine@hg-db:5432/hydrogenuine")


class StructuredDataStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or default_dsn()

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection[Any]]:
        conn = psycopg.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()

    def bootstrap_schema(self) -> dict[str, Any]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(SCHEMA_SQL)
                self._apply_v2_migrations(cur)
                cur.execute(
                    """
                    INSERT INTO storage_schema_versions(schema_name, schema_version)
                    VALUES (%s, %s)
                    ON CONFLICT (schema_name)
                    DO UPDATE SET schema_version = EXCLUDED.schema_version, applied_at = now()
                    """,
                    ("storage_substrate", SCHEMA_VERSION),
                )
                cur.execute(
                    """
                    INSERT INTO storage_migration_ledger(migration_id, from_version, to_version, applied, dry_run, sql_digest)
                    VALUES (%s, %s, %s, true, false, %s)
                    ON CONFLICT (migration_id) DO NOTHING
                    """,
                    (
                        f"bootstrap_{SCHEMA_VERSION}",
                        None,
                        SCHEMA_VERSION,
                        stable_hash(SCHEMA_SQL),
                    ),
                )
            conn.commit()
        return {"schema_bootstrapped": True, "schema_version": SCHEMA_VERSION, **authority_fields()}

    @staticmethod
    def _apply_v2_migrations(cur: Any) -> None:
        v2_alters = [
            ("v2_vmr_namespace", "ALTER TABLE vector_memory_records ADD COLUMN IF NOT EXISTS namespace text NOT NULL DEFAULT 'default'"),
            ("v2_vmr_provider", "ALTER TABLE vector_memory_records ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'deterministic_fixture'"),
            ("v2_blob_class", "ALTER TABLE blob_artifacts ADD COLUMN IF NOT EXISTS artifact_class text NOT NULL DEFAULT 'UNKNOWN_REVIEW_REQUIRED'"),
            ("v2_backup_schema", "ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS schema_version text NOT NULL DEFAULT 'storage_substrate_v1'"),
            ("v2_proof_gate", "ALTER TABLE proof_artifacts ADD COLUMN IF NOT EXISTS gate_name text"),
            ("v2_proof_verdict", "ALTER TABLE proof_artifacts ADD COLUMN IF NOT EXISTS verdict text"),
        ]
        for migration_id, sql in v2_alters:
            cur.execute(
                "SELECT 1 FROM storage_migration_ledger WHERE migration_id = %s",
                (migration_id,),
            )
            if not cur.fetchone():
                cur.execute(sql)
                cur.execute(
                    """
                    INSERT INTO storage_migration_ledger(migration_id, from_version, to_version, applied, dry_run, sql_digest)
                    VALUES (%s, %s, %s, true, false, %s)
                    ON CONFLICT (migration_id) DO NOTHING
                    """,
                    (migration_id, "storage_substrate_v1", "storage_substrate_v2", stable_hash(sql)),
                )

    def dry_run_migration(self) -> dict[str, Any]:
        statements = [stmt.strip() for stmt in SCHEMA_SQL.split(";") if stmt.strip()]
        return {
            "dry_run": True,
            "changes_applied": False,
            "sql_statements": statements,
            "statement_count": len(statements),
            "schema_version": SCHEMA_VERSION,
            "sql_digest": stable_hash(SCHEMA_SQL),
            **authority_fields(),
        }

    def schema_version(self) -> str:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT schema_version FROM storage_schema_versions WHERE schema_name = %s", ("storage_substrate",))
                row = cur.fetchone()
        return str(row[0]) if row else "missing"

    def detect_stale_schema(self) -> dict[str, Any]:
        current = self.schema_version()
        is_stale = current != SCHEMA_VERSION
        return {
            "stale": is_stale,
            "current_version": current,
            "expected_version": SCHEMA_VERSION,
            **authority_fields(),
        }

    def insert_structured_record(self, record_id: str, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        require_non_authority(payload)
        record = {
            "record_id": record_id,
            "record_type": record_type,
            "payload": payload,
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        record_hash = stable_hash(record)
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO structured_state_records(record_id, record_type, payload, hash)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (record_id) DO UPDATE
                    SET record_type = EXCLUDED.record_type, payload = EXCLUDED.payload, hash = EXCLUDED.hash
                    """,
                    (record_id, record_type, stable_json(payload), record_hash),
                )
            conn.commit()
        record["hash"] = record_hash
        return record

    def emit_receipt(self, receipt_id: str, receipt_type: str, subsystem: str, payload: dict[str, Any]) -> dict[str, Any]:
        require_non_authority(payload)
        receipt = {
            "receipt_id": receipt_id,
            "receipt_type": receipt_type,
            "subsystem": subsystem,
            "payload": payload,
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        receipt_hash = stable_hash(receipt)
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO storage_receipts(receipt_id, receipt_type, subsystem, payload, hash)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (receipt_id) DO UPDATE
                    SET receipt_type = EXCLUDED.receipt_type, subsystem = EXCLUDED.subsystem,
                        payload = EXCLUDED.payload, hash = EXCLUDED.hash
                    """,
                    (receipt_id, receipt_type, subsystem, stable_json(payload), receipt_hash),
                )
            conn.commit()
        receipt["hash"] = receipt_hash
        return receipt

    def rollback_plan(self) -> dict[str, Any]:
        return {
            "rollback_type": "schema_rollback_plan",
            "current_version": SCHEMA_VERSION,
            "action": "DROP tables and re-bootstrap from prior version",
            "destructive": True,
            "executed": False,
            "reason": "rollback_plans_are_advisory_only",
            **authority_fields(),
        }
