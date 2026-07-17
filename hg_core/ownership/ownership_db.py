"""
SQLite schema for ownership ledger and state. Used by OwnershipLedger and OwnershipStore.
Phase 4 adds FTS5 and graph tables in the same DB.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def _conn(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def with_transaction(db_path: str, callback):
    """
    Run callback(conn) in a single transaction. COMMIT on success, ROLLBACK on exception.
    Use for atomic multi-step operations (e.g. ledger_append + state_cas_update).
    """
    init_ownership_schema(db_path)
    c = _conn(db_path)
    try:
        callback(c)
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_ownership_schema(db_path: str) -> None:
    """Create ownership_events and ownership_state tables if not exist."""
    with _conn(db_path) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS ownership_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                type TEXT NOT NULL,
                actor TEXT NOT NULL,
                ts REAL NOT NULL,
                expected_version INTEGER,
                payload TEXT NOT NULL
            );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_ownership_events_run_task ON ownership_events(run_id, task_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ownership_events_ts ON ownership_events(ts);")

        c.execute("""
            CREATE TABLE IF NOT EXISTS ownership_state (
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                sponsor_id TEXT DEFAULT '',
                accountable_id TEXT DEFAULT '',
                executor_id TEXT DEFAULT '',
                current_token_id TEXT DEFAULT '',
                lease_expires_ts REAL DEFAULT 0,
                state TEXT DEFAULT 'assigned',
                approver_spec TEXT,
                escalation_spec TEXT,
                checkpoint_id TEXT,
                last_event_ts REAL DEFAULT 0,
                contested_claims TEXT,
                PRIMARY KEY (run_id, task_id)
            );
        """)
        try:
            c.execute("ALTER TABLE ownership_state ADD COLUMN contested_claims TEXT")
        except sqlite3.OperationalError:
            pass
        # Phase 4: FTS5 for event search
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ownership_fts USING fts5(
                content,
                run_id,
                task_id,
                event_id,
                type,
                actor,
                ts,
                tokenize='unicode61'
            );
        """)
        # Phase 4: graph tables for ownership chain view
        c.execute("""
            CREATE TABLE IF NOT EXISTS ownership_chain (
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                sponsor_id TEXT DEFAULT '',
                accountable_id TEXT DEFAULT '',
                executor_id TEXT DEFAULT '',
                approver_id TEXT DEFAULT '',
                state TEXT DEFAULT 'assigned',
                updated_ts REAL NOT NULL,
                PRIMARY KEY (run_id, task_id)
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ownership_chain_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                from_principal TEXT NOT NULL,
                to_principal TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                updated_ts REAL NOT NULL
            );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_ownership_chain_run ON ownership_chain(run_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ownership_chain_edges_run_task ON ownership_chain_edges(run_id, task_id);")
        c.commit()


def _ledger_append_conn(
    c: sqlite3.Connection,
    run_id: str,
    task_id: str,
    type_: str,
    actor: str,
    ts: float,
    payload: Dict[str, Any],
    expected_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Append one event row using existing connection (no commit). Use inside with_transaction for ACID."""
    import uuid
    event_id = str(uuid.uuid4())
    payload_json = json.dumps(payload, ensure_ascii=False)
    content = " ".join([type_, actor, task_id, payload_json])
    c.execute("""
        INSERT INTO ownership_events (run_id, task_id, event_id, type, actor, ts, expected_version, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, task_id, event_id, type_, actor, ts, expected_version, payload_json))
    c.execute("""
        INSERT INTO ownership_fts (content, run_id, task_id, event_id, type, actor, ts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (content, run_id, task_id, event_id, type_, actor, ts))
    return {
        "ts": ts,
        "run_id": run_id,
        "task_id": task_id,
        "event_id": event_id,
        "type": type_,
        "actor": actor,
        "expected_version": expected_version,
        **payload,
    }


def ledger_append(
    db_path: str,
    run_id: str,
    task_id: str,
    type_: str,
    actor: str,
    ts: float,
    payload: Dict[str, Any],
    expected_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Append one event row. Returns event dict with event_id from last row id or payload."""
    init_ownership_schema(db_path)
    result: List[Optional[Dict[str, Any]]] = [None]

    def do(c: sqlite3.Connection):
        result[0] = _ledger_append_conn(c, run_id, task_id, type_, actor, ts, payload, expected_version)

    with_transaction(db_path, do)
    assert result[0] is not None
    return result[0]


def _state_get_conn(c: sqlite3.Connection, run_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Get one state row as dict from existing connection, or None if missing."""
    row = c.execute(
        "SELECT * FROM ownership_state WHERE run_id = ? AND task_id = ?",
        (run_id, task_id),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    for key in ("approver_spec", "escalation_spec", "contested_claims"):
        if d.get(key) and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                pass
    return d


def state_get(db_path: str, run_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Get one state row as dict, or None if missing."""
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        return _state_get_conn(c, run_id, task_id)


def _state_cas_update_conn(
    c: sqlite3.Connection,
    db_path: str,
    run_id: str,
    task_id: str,
    expected_version: int,
    mutate_fn,
) -> tuple:
    """
    CAS update using existing connection (no commit). Returns (ok, record, error).
    Use inside with_transaction for ACID with ledger_append.
    """
    from .ownership_models import OwnershipRecord

    row = _state_get_conn(c, run_id, task_id)
    if row is None:
        raw = {"task_id": task_id, "version": 0}
    else:
        raw = dict(row)
    cur_ver = int(raw.get("version", 0))
    if cur_ver != expected_version:
        return False, None, "VERSION_CONFLICT"
    contested = raw.get("contested_claims")
    if contested and isinstance(contested, str):
        try:
            contested = json.loads(contested)
        except Exception:
            contested = None
    rec = OwnershipRecord(
        task_id=raw.get("task_id", task_id),
        version=raw.get("version", 0),
        sponsor_id=raw.get("sponsor_id", "") or "",
        accountable_id=raw.get("accountable_id", "") or "",
        executor_id=raw.get("executor_id", "") or "",
        current_token_id=raw.get("current_token_id", "") or "",
        lease_expires_ts=float(raw.get("lease_expires_ts") or 0),
        state=raw.get("state", "assigned") or "assigned",
        approver_spec=raw.get("approver_spec"),
        escalation_spec=raw.get("escalation_spec"),
        checkpoint_id=raw.get("checkpoint_id"),
        last_event_ts=float(raw.get("last_event_ts") or 0),
        contested_claims=contested,
    )
    mutate_fn(rec)
    rec.version = cur_ver + 1
    import time
    rec.last_event_ts = time.time()
    approver_spec_json = json.dumps(rec.approver_spec) if rec.approver_spec else None
    escalation_spec_json = json.dumps(rec.escalation_spec) if rec.escalation_spec else None
    contested_json = json.dumps(rec.contested_claims) if rec.contested_claims else None
    approver_id = ""
    if rec.approver_spec and rec.approver_spec.get("kind") == "principal":
        approver_id = rec.approver_spec.get("value") or ""

    c.execute("""
        INSERT OR REPLACE INTO ownership_state (
            run_id, task_id, version, sponsor_id, accountable_id, executor_id,
            current_token_id, lease_expires_ts, state, approver_spec, escalation_spec,
            checkpoint_id, last_event_ts, contested_claims
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, task_id, rec.version,
        rec.sponsor_id or "", rec.accountable_id or "", rec.executor_id or "",
        rec.current_token_id or "", rec.lease_expires_ts, rec.state,
        approver_spec_json, escalation_spec_json,
        rec.checkpoint_id, rec.last_event_ts, contested_json,
    ))
    c.execute("""
        INSERT OR REPLACE INTO ownership_chain (
            run_id, task_id, sponsor_id, accountable_id, executor_id, approver_id, state, updated_ts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, task_id,
        rec.sponsor_id or "", rec.accountable_id or "", rec.executor_id or "",
        approver_id, rec.state, rec.last_event_ts,
    ))
    c.execute("DELETE FROM ownership_chain_edges WHERE run_id = ? AND task_id = ?", (run_id, task_id))
    edges = []
    if rec.sponsor_id and rec.accountable_id:
        edges.append((run_id, task_id, rec.sponsor_id, rec.accountable_id, "accountable", rec.last_event_ts))
    if rec.accountable_id and rec.executor_id:
        edges.append((run_id, task_id, rec.accountable_id, rec.executor_id, "executor", rec.last_event_ts))
    if rec.executor_id and approver_id:
        edges.append((run_id, task_id, rec.executor_id, approver_id, "approver", rec.last_event_ts))
    for e in edges:
        c.execute("""
            INSERT INTO ownership_chain_edges (run_id, task_id, from_principal, to_principal, edge_type, updated_ts)
            VALUES (?, ?, ?, ?, ?, ?)
        """, e)
    return True, rec, None


def state_cas_update(
    db_path: str,
    run_id: str,
    task_id: str,
    expected_version: int,
    mutate_fn,
) -> tuple:
    """
    CAS update: load row, call mutate_fn(OwnershipRecord), write back if version matches.
    Returns (ok: bool, record: Optional[OwnershipRecord], error: Optional[str]).
    Uses single transaction for ACID.
    """
    init_ownership_schema(db_path)
    result: List[Optional[tuple]] = [None]

    def do(c: sqlite3.Connection):
        result[0] = _state_cas_update_conn(c, db_path, run_id, task_id, expected_version, mutate_fn)

    with_transaction(db_path, do)
    assert result[0] is not None
    return result[0]


def state_list_expired_leases(
    db_path: str,
    run_id: str,
    now_ts: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return state rows for tasks with lease_expires_ts in (0, now_ts) and state in acknowledged/in_progress."""
    import time
    if now_ts is None:
        now_ts = time.time()
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        rows = c.execute("""
            SELECT * FROM ownership_state
            WHERE run_id = ? AND lease_expires_ts > 0 AND lease_expires_ts < ?
            AND state IN ('acknowledged', 'in_progress')
        """, (run_id, now_ts)).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        for key in ("approver_spec", "escalation_spec", "contested_claims"):
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        out.append(d)
    return out


def state_list_contested(db_path: str, run_id: str) -> List[Dict[str, Any]]:
    """Return state rows for tasks with state = 'contested' in this run's ownership db."""
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT * FROM ownership_state WHERE run_id = ? AND state = ?",
            (run_id, "contested"),
        ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        for key in ("approver_spec", "escalation_spec", "contested_claims"):
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        out.append(d)
    return out


def search_events_fts(
    db_path: str,
    run_id: str,
    query: str,
    task_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Full-text search over ownership events. Returns matching events with run_id/task_id/type/actor/ts."""
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        if task_id:
            rows = c.execute("""
                SELECT run_id, task_id, event_id, type, actor, ts
                FROM ownership_fts WHERE ownership_fts MATCH ? AND run_id = ? AND task_id = ?
                ORDER BY ts DESC LIMIT ?
            """, (query, run_id, task_id, limit)).fetchall()
        else:
            rows = c.execute("""
                SELECT run_id, task_id, event_id, type, actor, ts
                FROM ownership_fts WHERE ownership_fts MATCH ? AND run_id = ?
                ORDER BY ts DESC LIMIT ?
            """, (query, run_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_chain(
    db_path: str,
    run_id: str,
    task_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return ownership chain rows (current snapshot per task). If task_id given, one row else all for run."""
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        if task_id:
            rows = c.execute(
                "SELECT * FROM ownership_chain WHERE run_id = ? AND task_id = ?",
                (run_id, task_id),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM ownership_chain WHERE run_id = ? ORDER BY task_id", (run_id,)).fetchall()
    return [dict(r) for r in rows]


def get_chain_edges(
    db_path: str,
    run_id: str,
    task_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return ownership chain edges (from_principal, to_principal, edge_type) for graph view."""
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        if task_id:
            rows = c.execute(
                "SELECT run_id, task_id, from_principal, to_principal, edge_type, updated_ts FROM ownership_chain_edges WHERE run_id = ? AND task_id = ?",
                (run_id, task_id),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT run_id, task_id, from_principal, to_principal, edge_type, updated_ts FROM ownership_chain_edges WHERE run_id = ? ORDER BY task_id",
                (run_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def ledger_list_events(
    db_path: str,
    run_id: str,
    task_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List events for run_id, optionally filtered by task_id."""
    init_ownership_schema(db_path)
    with _conn(db_path) as c:
        if task_id is not None:
            q = "SELECT * FROM ownership_events WHERE run_id = ? AND task_id = ? ORDER BY id ASC"
            params = (run_id, task_id)
        else:
            q = "SELECT * FROM ownership_events WHERE run_id = ? ORDER BY id ASC"
            params = (run_id,)
        if limit is not None:
            q += " LIMIT ?"
            params = params + (limit,)
        rows = c.execute(q, params).fetchall()
    out = []
    for row in rows:
        r = dict(row)
        try:
            payload = json.loads(r.pop("payload", "{}"))
        except Exception:
            payload = {}
        r.update(payload)
        out.append(r)
    return out
