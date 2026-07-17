"""Persistent idempotency store for tool calls: key -> result (or error), TTL. SQLite default."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from hg_gateway.db import get_connection
from hg_realtime.storage_config import runtime_store_backend


def _default_ttl_s() -> int:
    return int(os.getenv("HG_IDEMPOTENCY_TTL_S", "86400"))  # 24h


class IdempotencyStore(ABC):
    """Store for tool call results by idempotency_key. Check before execute; write after."""

    @abstractmethod
    def get(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Return cached result if present and not expired; else None."""
        ...

    @abstractmethod
    def set(
        self,
        idempotency_key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store result (or error payload). ttl_seconds defaults to env HG_IDEMPOTENCY_TTL_S or 86400."""
        ...


class InMemoryIdempotencyStore(IdempotencyStore):
    """In-memory idempotency store for tests or when SQLite is unavailable."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Dict[str, Any], float]] = {}  # key -> (value, expires_at)

    def get(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        entry = self._store.get(idempotency_key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[idempotency_key]
            return None
        return value

    def set(
        self,
        idempotency_key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else _default_ttl_s()
        self._store[idempotency_key] = (value, time.time() + ttl)


class SqliteIdempotencyStore(IdempotencyStore):
    """SQLite-backed idempotency store. One table: key, value (JSON), expires_at."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            self._path = db_path
        elif os.getenv("HG_IDEMPOTENCY_DB_PATH"):
            self._path = os.getenv("HG_IDEMPOTENCY_DB_PATH")
        else:
            base = Path(os.getenv("HG_DB_PATH", "hg_console.db")).resolve().parent
            self._path = str(base / "hg_idempotency.sqlite")
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency(expires_at)")
            c.commit()

    def get(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        with self._conn() as c:
            row = c.execute(
                "SELECT value, expires_at FROM idempotency WHERE idempotency_key = ? AND expires_at > ?",
                (idempotency_key, now),
            ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None

    def set(
        self,
        idempotency_key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else _default_ttl_s()
        expires_at = time.time() + ttl
        payload = json.dumps(value, separators=(",", ":"))
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO idempotency(idempotency_key, value, expires_at) VALUES (?, ?, ?)",
                (idempotency_key, payload, expires_at),
            )
            c.commit()


class GatewayIdempotencyStore(IdempotencyStore):
    """Gateway-backed idempotency store using the shared runtime database."""

    def get(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        with get_connection() as c:
            row = c.execute(
                "SELECT value, expires_at FROM idempotency WHERE idempotency_key = ? AND expires_at > ?",
                (idempotency_key, now),
            ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def set(
        self,
        idempotency_key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else _default_ttl_s()
        expires_at = time.time() + ttl
        payload = json.dumps(value, separators=(",", ":"))
        with get_connection() as c:
            c.execute(
                "INSERT OR REPLACE INTO idempotency(idempotency_key, value, expires_at) VALUES (?, ?, ?)",
                (idempotency_key, payload, expires_at),
            )


def default_idempotency_store(db_path: Optional[str] = None) -> IdempotencyStore:
    backend = runtime_store_backend()
    if backend in {"sqlite", "postgres"} and db_path is None:
        return GatewayIdempotencyStore()
    return SqliteIdempotencyStore(db_path=db_path)
