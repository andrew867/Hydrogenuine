"""Steering command store adapters for shared gateway DB and legacy SQLite."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .contracts import SteeringEvent
from hg_realtime.storage_config import runtime_store_backend


def _default_db_path() -> str:
    return os.environ.get("HG_STEERING_DB_PATH") or str(
        Path(os.environ.get("HG_DB_PATH", "hg_console.db")).resolve().parent / "hg_steering.sqlite"
    )


def _gateway_store_backend() -> str:
    return runtime_store_backend()


class SqliteSteeringStore:
    """Legacy SQLite-backed steering command store."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._path = db_path or _default_db_path()
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS steering_events (
                    steering_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    node_id TEXT,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0
                )
            """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_steering_run_id ON steering_events(run_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_steering_run_consumed ON steering_events(run_id, consumed)")
            c.commit()

    def submit(self, evt: SteeringEvent) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO steering_events
                   (steering_id, run_id, node_id, kind, payload, created_at, consumed)
                   VALUES (?, ?, ?, ?, ?, ?, 0)""",
                (
                    evt.steering_id,
                    evt.run_id,
                    evt.node_id,
                    evt.kind,
                    json.dumps(evt.payload, default=str),
                    evt.created_at.isoformat() if evt.created_at else "",
                ),
            )
            c.commit()

    def get_pending(self, run_id: str) -> List[Dict[str, Any]]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                """SELECT steering_id, run_id, node_id, kind, payload, created_at
                   FROM steering_events WHERE run_id = ? AND consumed = 0 ORDER BY created_at ASC""",
                (run_id,),
            ).fetchall()
        return _rows_to_events(rows)

    def mark_consumed(self, steering_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE steering_events SET consumed = 1 WHERE steering_id = ?", (steering_id,))
            c.commit()


class GatewaySteeringStore:
    """Shared gateway-db steering command store."""

    def _conn(self):
        from hg_gateway.db import get_connection

        return get_connection()

    def submit(self, evt: SteeringEvent) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO steering_events
                   (steering_id, run_id, node_id, kind, payload, created_at, consumed)
                   VALUES (?, ?, ?, ?, ?, ?, 0)""",
                (
                    evt.steering_id,
                    evt.run_id,
                    evt.node_id,
                    evt.kind,
                    json.dumps(evt.payload, default=str),
                    evt.created_at.isoformat() if evt.created_at else "",
                ),
            )

    def get_pending(self, run_id: str) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT steering_id, run_id, node_id, kind, payload, created_at
                   FROM steering_events WHERE run_id = ? AND consumed = 0 ORDER BY created_at ASC""",
                (run_id,),
            ).fetchall()
        return _rows_to_events(rows)

    def mark_consumed(self, steering_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE steering_events SET consumed = 1 WHERE steering_id = ?", (steering_id,))


def _rows_to_events(rows: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        payload = {}
        try:
            payload = json.loads(r["payload"]) if r["payload"] else {}
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        out.append(
            {
                "steering_id": r["steering_id"],
                "run_id": r["run_id"],
                "node_id": r["node_id"],
                "kind": r["kind"],
                "payload": payload,
                "created_at": r["created_at"],
            }
        )
    return out


def default_steering_store(db_path: Optional[str] = None):
    backend = _gateway_store_backend()
    if backend in {"sqlite", "postgres"} and db_path is None:
        return GatewaySteeringStore()
    return SqliteSteeringStore(db_path=db_path)
