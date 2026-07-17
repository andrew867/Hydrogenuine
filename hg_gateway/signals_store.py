"""
Pack 15: Store layer for signal_events and signal_features. Tenant-scoped; uses gateway DB.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def signal_event_insert(
    *,
    tenant_id: str,
    chat_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    direction: str,
    signals_json: Dict[str, Any],
    text_sha256: Optional[str] = None,
    provenance_json: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    event_id: Optional[str] = None,
    tags: str = "",
    explanation: str = "",
) -> str:
    """Insert a signal_event and optional signal_events_fts row. Returns event_id."""
    event_id = event_id or str(uuid.uuid4())
    timestamp = _now()
    signals_str = json.dumps(signals_json, ensure_ascii=False)
    prov_str = json.dumps(provenance_json) if provenance_json else None
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO signal_events (
            event_id, tenant_id, chat_id, turn_id, entity_id, direction, timestamp,
            signals_json, text_sha256, provenance_json, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                tenant_id,
                chat_id,
                turn_id,
                entity_id,
                direction,
                timestamp,
                signals_str,
                text_sha256,
                prov_str,
                trace_id,
            ),
        )
        try:
            conn.execute(
                """INSERT INTO signal_events_fts (event_id, tenant_id, chat_id, entity_id, tags, explanation)
                 VALUES (?, ?, ?, ?, ?, ?)""",
                (event_id, tenant_id or "", chat_id or "", entity_id or "", tags or "", explanation or ""),
            )
        except Exception:
            pass
    return event_id


def signal_feature_insert(
    *,
    event_id: str,
    tenant_id: str,
    feature_key: str,
    feature_value: float,
) -> None:
    """Insert a signal_features row."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO signal_features (event_id, tenant_id, feature_key, feature_value, created_at)
             VALUES (?, ?, ?, ?, ?)""",
            (event_id, tenant_id, feature_key, feature_value, _now()),
        )


def signal_events_list(
    tenant_id: str,
    *,
    chat_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List signal_events for tenant, optionally filtered by chat_id, entity_id, and timestamp range (ISO)."""
    with get_connection() as conn:
        conditions = ["tenant_id = ?"]
        params: List[Any] = [tenant_id]
        if chat_id:
            conditions.append("chat_id = ?")
            params.append(chat_id)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if from_ts:
            conditions.append("timestamp >= ?")
            params.append(from_ts)
        if to_ts:
            conditions.append("timestamp <= ?")
            params.append(to_ts)
        where = " AND ".join(conditions)
        params.extend([limit, offset])
        rows = conn.execute(
            f"""SELECT event_id, tenant_id, chat_id, turn_id, entity_id, direction, timestamp,
                signals_json, text_sha256, provenance_json, trace_id
                FROM signal_events WHERE {where}
                ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "event_id": r["event_id"],
                "tenant_id": r["tenant_id"],
                "chat_id": r["chat_id"],
                "turn_id": r["turn_id"],
                "entity_id": r["entity_id"],
                "direction": r["direction"],
                "timestamp": r["timestamp"],
                "signals_json": json.loads(r["signals_json"]) if r["signals_json"] else {},
                "text_sha256": r["text_sha256"],
                "provenance_json": json.loads(r["provenance_json"]) if r["provenance_json"] else None,
                "trace_id": r["trace_id"],
            })
        return out


def signal_events_fts_search(
    tenant_id: str,
    query: str,
    *,
    limit: int = 50,
) -> List[str]:
    """Search signal_events_fts for matching event_ids (tenant-scoped). Returns list of event_id."""
    if not query or not query.strip():
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT event_id FROM signal_events_fts
             WHERE signal_events_fts MATCH ? AND tenant_id = ?
             LIMIT ?""",
            (query.strip(), tenant_id, limit),
        ).fetchall()
        return [r["event_id"] for r in rows]


def signal_events_export_for_proof(
    tenant_id: str,
    chat_id: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Export signal_events for proof bundles (tenant-scoped, optional chat)."""
    return signal_events_list(tenant_id, chat_id=chat_id, limit=limit, offset=0)
