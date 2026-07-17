from __future__ import annotations

import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from hg_realtime.storage_config import runtime_store_backend


def _gateway_store_backend() -> str:
    return runtime_store_backend()


@dataclass(frozen=True)
class Lease:
    run_id: str
    lease_id: str
    worker_id: str
    acquired_at: float
    last_heartbeat_at: float
    seq: int


class RunLeaseStore:
    """Legacy SQLite-backed run leases with reclaim and reaping."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
            CREATE TABLE IF NOT EXISTS run_leases (
                run_id TEXT PRIMARY KEY,
                lease_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                acquired_at REAL NOT NULL,
                last_heartbeat_at REAL NOT NULL,
                seq INTEGER NOT NULL
            )
            """
            )
            c.commit()

    def acquire(self, *, run_id: str, worker_id: str, stale_after_s: float = 30.0) -> Lease:
        now = time.time()
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, lease_id, worker_id, acquired_at, last_heartbeat_at, seq FROM run_leases WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None:
                lease_id = str(uuid.uuid4())
                c.execute(
                    "INSERT INTO run_leases(run_id, lease_id, worker_id, acquired_at, last_heartbeat_at, seq) VALUES (?,?,?,?,?,?)",
                    (run_id, lease_id, worker_id, now, now, 0),
                )
                c.commit()
                return Lease(run_id, lease_id, worker_id, now, now, 0)

            (_, _, wid, _, last_hb, _) = row
            if now - float(last_hb) > stale_after_s:
                new_lease = str(uuid.uuid4())
                c.execute(
                    "UPDATE run_leases SET lease_id=?, worker_id=?, acquired_at=?, last_heartbeat_at=?, seq=? WHERE run_id=?",
                    (new_lease, worker_id, now, now, 0, run_id),
                )
                c.commit()
                return Lease(run_id, new_lease, worker_id, now, now, 0)

            raise RuntimeError(f"run {run_id} is already leased by {wid}")

    def heartbeat(self, *, run_id: str, lease_id: str, worker_id: str, seq: int) -> None:
        now = time.time()
        with self._conn() as c:
            row = c.execute("SELECT lease_id, worker_id, seq FROM run_leases WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise RuntimeError("no lease to heartbeat")
            cur_lease, cur_worker, cur_seq = row
            if cur_lease != lease_id or cur_worker != worker_id:
                raise RuntimeError("lease mismatch")
            if seq <= int(cur_seq):
                raise RuntimeError("non-monotonic heartbeat seq")
            c.execute("UPDATE run_leases SET last_heartbeat_at=?, seq=? WHERE run_id=?", (now, seq, run_id))
            c.commit()

    def get(self, *, run_id: str) -> Optional[Lease]:
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, lease_id, worker_id, acquired_at, last_heartbeat_at, seq FROM run_leases WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            return Lease(*row)

    def release(self, run_id: str) -> bool:
        with self._conn() as c:
            c.execute("DELETE FROM run_leases WHERE run_id=?", (run_id,))
            n = c.execute("SELECT changes()").fetchone()[0]
            c.commit()
            return n > 0

    def reap_stale(self, *, stale_after_s: float = 60.0) -> int:
        now = time.time()
        with self._conn() as c:
            rows = c.execute("SELECT run_id, last_heartbeat_at FROM run_leases").fetchall()
            stale = [rid for (rid, hb) in rows if now - float(hb) > stale_after_s]
            for rid in stale:
                c.execute("DELETE FROM run_leases WHERE run_id=?", (rid,))
            c.commit()
            return len(stale)


class GatewayRunLeaseStore:
    """Run leases backed by the shared gateway database layer."""

    def _conn(self):
        from hg_gateway.db import get_connection

        return get_connection()

    def acquire(self, *, run_id: str, worker_id: str, stale_after_s: float = 30.0) -> Lease:
        now = time.time()
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, lease_id, worker_id, acquired_at, last_heartbeat_at, seq FROM run_leases WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None:
                lease_id = str(uuid.uuid4())
                c.execute(
                    "INSERT INTO run_leases(run_id, lease_id, worker_id, acquired_at, last_heartbeat_at, seq) VALUES (?,?,?,?,?,?)",
                    (run_id, lease_id, worker_id, now, now, 0),
                )
                return Lease(run_id, lease_id, worker_id, now, now, 0)

            wid = row["worker_id"]
            last_hb = row["last_heartbeat_at"]
            if now - float(last_hb) > stale_after_s:
                new_lease = str(uuid.uuid4())
                c.execute(
                    "UPDATE run_leases SET lease_id=?, worker_id=?, acquired_at=?, last_heartbeat_at=?, seq=? WHERE run_id=?",
                    (new_lease, worker_id, now, now, 0, run_id),
                )
                return Lease(run_id, new_lease, worker_id, now, now, 0)

            raise RuntimeError(f"run {run_id} is already leased by {wid}")

    def heartbeat(self, *, run_id: str, lease_id: str, worker_id: str, seq: int) -> None:
        now = time.time()
        with self._conn() as c:
            row = c.execute("SELECT lease_id, worker_id, seq FROM run_leases WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise RuntimeError("no lease to heartbeat")
            cur_lease = row["lease_id"]
            cur_worker = row["worker_id"]
            cur_seq = row["seq"]
            if cur_lease != lease_id or cur_worker != worker_id:
                raise RuntimeError("lease mismatch")
            if seq <= int(cur_seq):
                raise RuntimeError("non-monotonic heartbeat seq")
            c.execute("UPDATE run_leases SET last_heartbeat_at=?, seq=? WHERE run_id=?", (now, seq, run_id))

    def get(self, *, run_id: str) -> Optional[Lease]:
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, lease_id, worker_id, acquired_at, last_heartbeat_at, seq FROM run_leases WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            return Lease(
                row["run_id"],
                row["lease_id"],
                row["worker_id"],
                float(row["acquired_at"]),
                float(row["last_heartbeat_at"]),
                int(row["seq"]),
            )

    def release(self, run_id: str) -> bool:
        with self._conn() as c:
            before = c.execute("SELECT run_id FROM run_leases WHERE run_id=?", (run_id,)).fetchone()
            c.execute("DELETE FROM run_leases WHERE run_id=?", (run_id,))
            return before is not None

    def reap_stale(self, *, stale_after_s: float = 60.0) -> int:
        now = time.time()
        with self._conn() as c:
            rows = c.execute("SELECT run_id, last_heartbeat_at FROM run_leases").fetchall()
            stale = [row["run_id"] for row in rows if now - float(row["last_heartbeat_at"]) > stale_after_s]
            for rid in stale:
                c.execute("DELETE FROM run_leases WHERE run_id=?", (rid,))
            return len(stale)


def default_lease_store(db_path: Optional[str] = None):
    backend = _gateway_store_backend()
    if backend in {"sqlite", "postgres"} and db_path is None:
        return GatewayRunLeaseStore()
    return RunLeaseStore(db_path or os.getenv("HG_LEASE_DB_PATH") or "hg_leases.sqlite")
