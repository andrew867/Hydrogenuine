"""L10 event store backed by the shared gateway database."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Generator, List, Optional


def _conn():
    from hg_gateway.db import get_connection

    return get_connection()


def _init() -> None:
    # Shared schema migration lives in hg_gateway.db.
    with _conn():
        return


def append_event(
    *,
    tenant_id: str,
    actor_id: str,
    correlation_id: str,
    payload: Dict[str, Any],
    event_type: str = "internal",
    event_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    _init()
    eid = event_id or str(uuid.uuid4())
    now = time.time()
    with _conn() as c:
        c.execute(
            """INSERT INTO l10_events(event_id, correlation_id, run_id, tenant_id, actor_id, event_type, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, correlation_id or "", run_id or "", tenant_id, actor_id, event_type, json.dumps(payload, default=str), now),
        )
    return eid


def list_events(
    *,
    correlation_id: Optional[str] = None,
    run_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    _init()
    with _conn() as c:
        if correlation_id and run_id:
            rows = c.execute(
                """SELECT event_id, correlation_id, run_id, tenant_id, actor_id, event_type, payload, created_at
                   FROM l10_events WHERE correlation_id = ? AND run_id = ? ORDER BY created_at DESC LIMIT ?""",
                (correlation_id, run_id, limit),
            ).fetchall()
        elif correlation_id:
            rows = c.execute(
                """SELECT event_id, correlation_id, run_id, tenant_id, actor_id, event_type, payload, created_at
                   FROM l10_events WHERE correlation_id = ? ORDER BY created_at DESC LIMIT ?""",
                (correlation_id, limit),
            ).fetchall()
        elif run_id:
            rows = c.execute(
                """SELECT event_id, correlation_id, run_id, tenant_id, actor_id, event_type, payload, created_at
                   FROM l10_events WHERE run_id = ? ORDER BY created_at DESC LIMIT ?""",
                (run_id, limit),
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT event_id, correlation_id, run_id, tenant_id, actor_id, event_type, payload, created_at
                   FROM l10_events ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    out = []
    for r in rows:
        try:
            payload = json.loads(r["payload"]) if r["payload"] else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        out.append(
            {
                "event_id": r["event_id"],
                "correlation_id": r["correlation_id"] or None,
                "run_id": r["run_id"] or None,
                "tenant_id": r["tenant_id"],
                "actor_id": r["actor_id"],
                "event_type": r["event_type"],
                "payload": payload,
                "created_at": r["created_at"],
            }
        )
    return out


def stream_events_sse(poll_interval: float = 1.0, last_created_at: Optional[float] = None) -> Generator[str, None, None]:
    yield "event: ready\ndata: {}\n\n"
    seen: set[str] = set()
    since = last_created_at or 0.0
    while True:
        _init()
        with _conn() as c:
            rows = c.execute(
                """SELECT event_id, correlation_id, run_id, tenant_id, actor_id, event_type, payload, created_at
                   FROM l10_events WHERE created_at > ? ORDER BY created_at ASC""",
                (since,),
            ).fetchall()
        for r in rows:
            eid = r["event_id"]
            if eid in seen:
                continue
            seen.add(eid)
            try:
                payload = json.loads(r["payload"]) if r["payload"] else {}
            except (json.JSONDecodeError, TypeError):
                payload = {}
            obj = {
                "event_id": r["event_id"],
                "correlation_id": r["correlation_id"] or None,
                "run_id": r["run_id"] or None,
                "tenant_id": r["tenant_id"],
                "actor_id": r["actor_id"],
                "event_type": r["event_type"],
                "payload": payload,
                "created_at": r["created_at"],
            }
            since = max(since, float(r["created_at"]))
            yield f"event: line\ndata: {json.dumps(obj, default=str)}\n\n"
        yield ": heartbeat\n\n"
        time.sleep(poll_interval)
