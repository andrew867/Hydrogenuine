"""Append Log Substrate — JSONL and Postgres backends."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from hg_core.storage_substrate.common import (
    SCHEMA_VERSION,
    append_jsonl,
    authority_fields,
    read_jsonl,
    require_non_authority,
    stable_hash,
    stable_json,
    utc_now_iso,
)


class AppendLogSubstrate:
    """Canonical append-only JSONL event/command log backend."""

    def __init__(self, path: "str | __builtins__"):
        from pathlib import Path

        self.path = Path(path)

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(payload)
        require_non_authority(payload)
        entries = read_jsonl(self.path)
        if event_id is not None:
            for existing in entries:
                if existing.get("event_id") == event_id:
                    return existing
        previous_hash = entries[-1]["hash"] if entries else None
        entry: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "seq": len(entries) + 1,
            "event_type": event_type,
            "event_id": event_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        entry["hash"] = stable_hash({k: v for k, v in entry.items() if k != "hash"})
        append_jsonl(self.path, entry)
        return entry

    def read(self) -> list[dict[str, Any]]:
        return read_jsonl(self.path)

    def replay_hash(self) -> str:
        return stable_hash(self.read())

    def verify_append_only(self) -> bool:
        previous_hash = None
        for index, entry in enumerate(self.read(), start=1):
            expected = stable_hash({k: v for k, v in entry.items() if k != "hash"})
            if entry.get("seq") != index or entry.get("previous_hash") != previous_hash or entry.get("hash") != expected:
                return False
            previous_hash = entry["hash"]
        return True

    def detect_chain_hash_mismatch(self) -> list[dict[str, Any]]:
        mismatches: list[dict[str, Any]] = []
        previous_hash = None
        for index, entry in enumerate(self.read(), start=1):
            if entry.get("previous_hash") != previous_hash:
                mismatches.append({"seq": index, "expected_previous": previous_hash, "actual_previous": entry.get("previous_hash")})
            previous_hash = entry.get("hash")
        return mismatches

    def refuse_prior_mutation(self) -> dict[str, Any]:
        return {
            "mutation_refused": True,
            "reason": "append_log_entries_are_append_only",
            **authority_fields(),
        }


class PostgresAppendLog:
    """Append-only event log backed by Postgres."""

    def __init__(self, stream_id: str, dsn: str | None = None):
        self.stream_id = stream_id
        self.dsn = dsn or os.environ.get("HG_STORAGE_POSTGRES_DSN", "postgresql://hydrogenuine:hydrogenuine@hg-db:5432/hydrogenuine")

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        import psycopg

        conn = psycopg.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(payload)
        require_non_authority(payload)
        with self._connect() as conn:
            with conn.cursor() as cur:
                if event_id is not None:
                    cur.execute(
                        "SELECT seq, event_type, payload, hash, created_at FROM append_log_entries WHERE stream_id = %s AND payload->>'event_id' = %s",
                        (self.stream_id, event_id),
                    )
                    row = cur.fetchone()
                    if row:
                        return {
                            "schema_version": SCHEMA_VERSION,
                            "seq": row[0],
                            "event_type": row[1],
                            "event_id": event_id,
                            "payload": row[2],
                            "hash": row[3],
                            **authority_fields(),
                        }
                cur.execute(
                    "SELECT seq, hash FROM append_log_entries WHERE stream_id = %s ORDER BY seq DESC LIMIT 1",
                    (self.stream_id,),
                )
                last = cur.fetchone()
                next_seq = (last[0] + 1) if last else 1
                previous_hash = last[1] if last else None
                entry: dict[str, Any] = {
                    "schema_version": SCHEMA_VERSION,
                    "seq": next_seq,
                    "event_type": event_type,
                    "event_id": event_id,
                    "payload": payload,
                    "previous_hash": previous_hash,
                    "created_at": utc_now_iso(),
                    **authority_fields(),
                }
                entry_hash = stable_hash({k: v for k, v in entry.items() if k != "hash"})
                entry["hash"] = entry_hash
                cur.execute(
                    """
                    INSERT INTO append_log_entries(stream_id, seq, event_type, payload, hash)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    """,
                    (self.stream_id, next_seq, event_type, stable_json(payload), entry_hash),
                )
            conn.commit()
        return entry

    def read(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT seq, event_type, payload, hash, created_at FROM append_log_entries WHERE stream_id = %s ORDER BY seq",
                    (self.stream_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "schema_version": SCHEMA_VERSION,
                "seq": row[0],
                "event_type": row[1],
                "payload": row[2],
                "hash": row[3],
                "created_at": str(row[4]),
                **authority_fields(),
            }
            for row in rows
        ]

    def replay_hash(self) -> str:
        return stable_hash(self.read())

    def verify_append_only(self) -> bool:
        entries = self.read()
        for index, entry in enumerate(entries, start=1):
            if entry.get("seq") != index:
                return False
        return True

    def refuse_prior_mutation(self) -> dict[str, Any]:
        return {
            "mutation_refused": True,
            "reason": "postgres_append_log_entries_are_append_only",
            **authority_fields(),
        }
