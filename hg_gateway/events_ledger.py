"""
Pack 25: Unified event stream and evidence ledger.

Append-only event_stream and evidence_ledger with hash chaining per (tenant_id, run_id|chat_id).
Canonicalization: JSON sorted keys UTF-8; text newline-normalized; binary raw bytes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection, _get_db_path

logger = logging.getLogger(__name__)


# --- Canonicalization ---

def _canonical_json(obj: Any) -> bytes:
    """Canonical JSON: sorted keys, UTF-8."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _canonical_text(text: str) -> bytes:
    """Text: newline normalize (\\n only)."""
    normalized = "\n".join((line.strip() for line in text.splitlines()))
    return normalized.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    """SHA256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    """SHA256 of canonical JSON."""
    return sha256_bytes(_canonical_json(obj))


def sha256_text(text: str) -> str:
    """SHA256 of canonical text."""
    return sha256_bytes(_canonical_text(text))


# --- Scope / partition ---

def _event_chain_key(tenant_id: str, run_id: Optional[str], chat_id: Optional[str]) -> str:
    """Partition key for event hash chain."""
    return f"{tenant_id}:{run_id or ''}:{chat_id or ''}"


def _ledger_partition_key(tenant_id: str, run_id: Optional[str], chat_id: Optional[str]) -> str:
    """Partition key for evidence ledger chain."""
    return f"{tenant_id}:{run_id or ''}:{chat_id or ''}"


def _event_prev_sha(conn: Any, tenant_id: str, run_id: Optional[str], chat_id: Optional[str]) -> Optional[str]:
    if run_id:
        prev = conn.execute(
            "SELECT event_sha256 FROM event_stream WHERE tenant_id = ? AND run_id = ? ORDER BY ts DESC LIMIT 1",
            (tenant_id, run_id),
        ).fetchone()
    else:
        prev = conn.execute(
            "SELECT event_sha256 FROM event_stream WHERE tenant_id = ? AND chat_id = ? ORDER BY ts DESC LIMIT 1",
            (tenant_id, chat_id or ""),
        ).fetchone()
    return prev["event_sha256"] if prev else None


def _ledger_prev_sha(conn: Any, tenant_id: str, run_id: Optional[str], chat_id: Optional[str]) -> Optional[str]:
    if run_id:
        prev = conn.execute(
            "SELECT ledger_sha256 FROM evidence_ledger WHERE tenant_id = ? AND run_id = ? ORDER BY ts DESC LIMIT 1",
            (tenant_id, run_id),
        ).fetchone()
    else:
        prev = conn.execute(
            "SELECT ledger_sha256 FROM evidence_ledger WHERE tenant_id = ? AND chat_id = ? ORDER BY ts DESC LIMIT 1",
            (tenant_id, chat_id or ""),
        ).fetchone()
    return prev["ledger_sha256"] if prev else None


def _emit_event_conn(
    conn: Any,
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    actor_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    run_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    document_id: Optional[str] = None,
    chunk_id: Optional[str] = None,
) -> str:
    event_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload_sha256 = sha256_json(payload)
    prev_event_sha256 = _event_prev_sha(conn, tenant_id, run_id, chat_id)
    chain_input = f"{prev_event_sha256 or ''}:{event_id}:{ts}:{payload_sha256}"
    event_sha256 = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
    conn.execute(
        """INSERT INTO event_stream (
            event_id, ts, tenant_id, actor_type, actor_id,
            run_id, chat_id, turn_id, tool_call_id, approval_id, document_id, chunk_id,
            event_type, payload_json, payload_sha256, prev_event_sha256, event_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id, ts, tenant_id, actor_type, actor_id,
            run_id, chat_id, turn_id, tool_call_id, approval_id, document_id, chunk_id,
            event_type, payload_json, payload_sha256, prev_event_sha256, event_sha256,
        ),
    )
    return event_id


def _append_evidence_conn(
    conn: Any,
    tenant_id: str,
    evidence_type: str,
    content_sha256: str,
    *,
    content_bytes: Optional[bytes] = None,
    content_ref: Optional[str] = None,
    redaction_applied: Optional[str] = None,
    run_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    document_id: Optional[str] = None,
    chunk_id: Optional[str] = None,
) -> str:
    ledger_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    prev_ledger_sha256 = _ledger_prev_sha(conn, tenant_id, run_id, chat_id)
    chain_input = f"{prev_ledger_sha256 or ''}:{ledger_id}:{ts}:{content_sha256}"
    ledger_sha256 = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
    conn.execute(
        """INSERT INTO evidence_ledger (
            ledger_id, ts, tenant_id, run_id, chat_id, turn_id, tool_call_id,
            approval_id, document_id, chunk_id, evidence_type,
            content_sha256, content_ref, content_bytes, redaction_applied,
            prev_ledger_sha256, ledger_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ledger_id, ts, tenant_id, run_id, chat_id, turn_id, tool_call_id,
            approval_id, document_id, chunk_id, evidence_type,
            content_sha256, content_ref, content_bytes, redaction_applied,
            prev_ledger_sha256, ledger_sha256,
        ),
    )
    return ledger_id


# --- Event stream ---

def emit_event(
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    actor_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    run_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    document_id: Optional[str] = None,
    chunk_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """
    Append one event to event_stream; compute payload_sha256 and chain event_sha256.
    Returns event_id.
    """
    with get_connection(db_path or _get_db_path()) as conn:
        return _emit_event_conn(
            conn,
            tenant_id,
            event_type,
            payload,
            actor_type=actor_type,
            actor_id=actor_id,
            run_id=run_id,
            chat_id=chat_id,
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            approval_id=approval_id,
            document_id=document_id,
            chunk_id=chunk_id,
        )


def emit_event_safe(
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    chat_id: Optional[str] = None,
    run_id: Optional[str] = None,
    **kwargs: Any,
) -> Optional[str]:
    """Emit event without raising; returns event_id or None on failure."""
    try:
        return emit_event(
            tenant_id,
            event_type,
            payload,
            chat_id=chat_id,
            run_id=run_id,
            **kwargs,
        )
    except Exception as e:
        logger.warning("events_ledger emit_event failed: %s", e, exc_info=False)
        return None


# --- Evidence ledger ---

def append_evidence(
    tenant_id: str,
    evidence_type: str,
    content_sha256: str,
    *,
    content_bytes: Optional[bytes] = None,
    content_ref: Optional[str] = None,
    redaction_applied: Optional[str] = None,
    run_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    document_id: Optional[str] = None,
    chunk_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """
    Append one row to evidence_ledger; compute ledger_sha256 chain.
    Returns ledger_id.
    """
    with get_connection(db_path or _get_db_path()) as conn:
        return _append_evidence_conn(
            conn,
            tenant_id,
            evidence_type,
            content_sha256,
            content_bytes=content_bytes,
            content_ref=content_ref,
            redaction_applied=redaction_applied,
            run_id=run_id,
            chat_id=chat_id,
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            approval_id=approval_id,
            document_id=document_id,
            chunk_id=chunk_id,
        )


# --- Query helpers for replay ---

def get_events_for_run(
    tenant_id: str,
    run_id: str,
    *,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    limit: int = 10_000,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load events for a run_id, optionally filtered by time and type."""
    with get_connection(db_path or _get_db_path()) as conn:
        q = """SELECT event_id, ts, tenant_id, actor_type, actor_id, run_id, chat_id,
                      turn_id, tool_call_id, approval_id, document_id, chunk_id,
                      event_type, payload_json, payload_sha256, prev_event_sha256, event_sha256
               FROM event_stream WHERE tenant_id = ? AND run_id = ?"""
        params: List[Any] = [tenant_id, run_id]
        if from_ts:
            q += " AND ts >= ?"
            params.append(from_ts)
        if to_ts:
            q += " AND ts <= ?"
            params.append(to_ts)
        if event_types:
            placeholders = ",".join("?" * len(event_types))
            q += f" AND event_type IN ({placeholders})"
            params.extend(event_types)
        q += " ORDER BY ts ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def get_evidence_for_run(
    tenant_id: str,
    run_id: str,
    *,
    evidence_types: Optional[List[str]] = None,
    limit: int = 10_000,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load evidence ledger rows for a run_id."""
    with get_connection(db_path or _get_db_path()) as conn:
        q = """SELECT ledger_id, ts, tenant_id, run_id, chat_id, turn_id, tool_call_id,
                      approval_id, document_id, chunk_id, evidence_type,
                      content_sha256, content_ref, redaction_applied, prev_ledger_sha256, ledger_sha256
               FROM evidence_ledger WHERE tenant_id = ? AND run_id = ?"""
        params: List[Any] = [tenant_id, run_id]
        if evidence_types:
            placeholders = ",".join("?" * len(evidence_types))
            q += f" AND evidence_type IN ({placeholders})"
            params.extend(evidence_types)
        q += " ORDER BY ts ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def list_events(
    tenant_id: str,
    *,
    run_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List events for tenant, filtered by run_id, chat_id, time range, types. Paginated."""
    with get_connection(db_path or _get_db_path()) as conn:
        q = """SELECT event_id, ts, tenant_id, actor_type, actor_id, run_id, chat_id,
                      turn_id, tool_call_id, approval_id, document_id, chunk_id,
                      event_type, payload_json, payload_sha256, prev_event_sha256, event_sha256
               FROM event_stream WHERE tenant_id = ?"""
        params: List[Any] = [tenant_id]
        if run_id:
            q += " AND run_id = ?"
            params.append(run_id)
        if chat_id:
            q += " AND chat_id = ?"
            params.append(chat_id)
        if from_ts:
            q += " AND ts >= ?"
            params.append(from_ts)
        if to_ts:
            q += " AND ts <= ?"
            params.append(to_ts)
        if event_types:
            placeholders = ",".join("?" * len(event_types))
            q += f" AND event_type IN ({placeholders})"
            params.extend(event_types)
        q += " ORDER BY ts DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def list_evidence(
    tenant_id: str,
    *,
    run_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    evidence_types: Optional[List[str]] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List evidence ledger rows for tenant, filtered by run_id or chat_id. Paginated."""
    with get_connection(db_path or _get_db_path()) as conn:
        q = """SELECT ledger_id, ts, tenant_id, run_id, chat_id, turn_id, tool_call_id,
                      approval_id, document_id, chunk_id, evidence_type,
                      content_sha256, content_ref, redaction_applied, prev_ledger_sha256, ledger_sha256
               FROM evidence_ledger WHERE tenant_id = ?"""
        params: List[Any] = [tenant_id]
        if run_id:
            q += " AND run_id = ?"
            params.append(run_id)
        if chat_id:
            q += " AND chat_id = ?"
            params.append(chat_id)
        if approval_id:
            q += " AND approval_id = ?"
            params.append(approval_id)
        if from_ts:
            q += " AND ts >= ?"
            params.append(from_ts)
        if to_ts:
            q += " AND ts <= ?"
            params.append(to_ts)
        if evidence_types:
            placeholders = ",".join("?" * len(evidence_types))
            q += f" AND evidence_type IN ({placeholders})"
            params.extend(evidence_types)
        q += " ORDER BY ts DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
