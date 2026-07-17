"""Realtime L10 event store backed by the shared gateway database."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional


def _conn():
    from hg_gateway.db import get_connection

    return get_connection()


def _init() -> None:
    with _conn():
        return


def append_event(
    *,
    tenant_id: str = "default",
    actor_id: str = "executor",
    correlation_id: str = "",
    payload: Dict[str, Any],
    event_type: str = "internal",
    event_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    try:
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
    except Exception:
        return ""
