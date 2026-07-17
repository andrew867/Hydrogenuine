"""Run index adapters for shared gateway DB and legacy SQLite."""

from __future__ import annotations

import os
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from hg_realtime.storage_config import runtime_store_backend


def _default_sqlite_path() -> str:
    return os.getenv("HG_DB_PATH", "./hg_console.db")


def _gateway_store_backend() -> str:
    return runtime_store_backend()


@dataclass(frozen=True)
class RunRecord:
    """One run row from the run index."""

    run_id: str
    workflow_id: str
    status: str
    started_at: Optional[float]
    ended_at: Optional[float]
    run_dir: Optional[str]
    correlation_id: Optional[str]


class RunIndexWriter(ABC):
    """Interface for writing run start (and optionally complete) to the run index."""

    @abstractmethod
    def record_start(
        self,
        *,
        run_id: str,
        workflow_id: str,
        job_id: Optional[str] = None,
        status: str = "running",
        correlation_id: Optional[str] = None,
        run_dir: Optional[str] = None,
        blocked_reason: Optional[str] = None,
        pending_request_json: Optional[str] = None,
    ) -> None:
        ...

    @abstractmethod
    def record_completion(self, *, run_id: str, status: str, completed_ts: float) -> None:
        ...


class RunIndexReader(ABC):
    @abstractmethod
    def get_run(self, run_id: str) -> Optional[RunRecord]:
        ...

    @abstractmethod
    def get_run_by_correlation_id(self, correlation_id: str) -> Optional[RunRecord]:
        ...


def _row_to_record(row: object) -> Optional[RunRecord]:
    if row is None:
        return None
    if isinstance(row, dict):
        data = row
    elif hasattr(row, "keys"):
        data = {key: row[key] for key in row.keys()}
    else:
        return None
    return RunRecord(
        run_id=str(data.get("run_id") or ""),
        workflow_id=str(data.get("graph_id") or ""),
        status=str(data.get("status") or ""),
        started_at=data.get("started_at"),
        ended_at=data.get("ended_at"),
        run_dir=data.get("run_dir"),
        correlation_id=data.get("correlation_id"),
    )


class SqliteRunIndexWriter(RunIndexWriter, RunIndexReader):
    """Legacy SQLite run index writer/reader."""

    def __init__(self, sqlite_path: Optional[str] = None) -> None:
        self._path = sqlite_path or _default_sqlite_path()

    def _init_db(self) -> None:
        with sqlite3.connect(self._path) as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS runs(
                  run_id TEXT PRIMARY KEY,
                  graph_id TEXT,
                  status TEXT,
                  started_at REAL,
                  ended_at REAL,
                  run_dir TEXT,
                  correlation_id TEXT
                );
            """
            )
            try:
                c.execute("ALTER TABLE runs ADD COLUMN correlation_id TEXT")
                c.commit()
            except sqlite3.OperationalError:
                pass
            c.commit()

    def record_start(
        self,
        *,
        run_id: str,
        workflow_id: str,
        job_id: Optional[str] = None,
        status: str = "running",
        correlation_id: Optional[str] = None,
        run_dir: Optional[str] = None,
        blocked_reason: Optional[str] = None,
        pending_request_json: Optional[str] = None,
    ) -> None:
        self._init_db()
        graph_id = workflow_id or job_id
        started_at = time.time()
        with sqlite3.connect(self._path) as c:
            try:
                c.execute("ALTER TABLE runs ADD COLUMN blocked_reason TEXT")
                c.commit()
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN pending_request_json TEXT")
                c.commit()
            except sqlite3.OperationalError:
                pass
            c.execute(
                """
                INSERT OR REPLACE INTO runs(run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id, blocked_reason, pending_request_json)
                VALUES(?,?,?,?,?,?,?,?,?)
            """,
                (run_id, graph_id, status, started_at, None, run_dir, correlation_id, blocked_reason, pending_request_json),
            )
            c.commit()

    def record_completion(self, *, run_id: str, status: str, completed_ts: float) -> None:
        self._init_db()
        with sqlite3.connect(self._path) as c:
            c.execute(
                "UPDATE runs SET status = ?, ended_at = ? WHERE run_id = ?",
                (status, completed_ts, run_id),
            )
            c.commit()

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        self._init_db()
        with sqlite3.connect(self._path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute(
                "SELECT run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _row_to_record(row)

    def get_run_by_correlation_id(self, correlation_id: str) -> Optional[RunRecord]:
        self._init_db()
        with sqlite3.connect(self._path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute(
                "SELECT run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id FROM runs WHERE correlation_id = ? ORDER BY started_at DESC LIMIT 1",
                (correlation_id,),
            ).fetchone()
        return _row_to_record(row)


class GatewayRunIndexWriter(RunIndexWriter, RunIndexReader):
    """Run index backed by the shared gateway database layer."""

    def _conn(self):
        from hg_gateway.db import get_connection

        return get_connection()

    def record_start(
        self,
        *,
        run_id: str,
        workflow_id: str,
        job_id: Optional[str] = None,
        status: str = "running",
        correlation_id: Optional[str] = None,
        run_dir: Optional[str] = None,
        blocked_reason: Optional[str] = None,
        pending_request_json: Optional[str] = None,
    ) -> None:
        graph_id = workflow_id or job_id
        started_at = time.time()
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO runs(run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id, blocked_reason, pending_request_json)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (run_id, graph_id, status, started_at, None, run_dir, correlation_id, blocked_reason, pending_request_json),
            )

    def record_completion(self, *, run_id: str, status: str, completed_ts: float) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE runs SET status = ?, ended_at = ? WHERE run_id = ?",
                (status, completed_ts, run_id),
            )

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _row_to_record(row)

    def get_run_by_correlation_id(self, correlation_id: str) -> Optional[RunRecord]:
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id FROM runs WHERE correlation_id = ? ORDER BY started_at DESC LIMIT 1",
                (correlation_id,),
            ).fetchone()
        return _row_to_record(row)


def default_run_index_writer(sqlite_path: Optional[str] = None) -> RunIndexWriter:
    backend = _gateway_store_backend()
    if backend in {"sqlite", "postgres"} and sqlite_path is None:
        return GatewayRunIndexWriter()
    return SqliteRunIndexWriter(sqlite_path=sqlite_path)


def default_run_index_reader(sqlite_path: Optional[str] = None) -> RunIndexReader:
    backend = _gateway_store_backend()
    if backend in {"sqlite", "postgres"} and sqlite_path is None:
        return GatewayRunIndexWriter()
    return SqliteRunIndexWriter(sqlite_path=sqlite_path)
