"""
Pack3 Phase 2: Idempotency and tool effect dedupe.

- Idempotency-Key header: same key + same request_hash -> return stored response; same key + different hash -> 409.
- Tool effects: effects_hash = hash(tool_name + args + target); re-execution returns cached result unless override.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from hg_gateway.db import get_connection, _get_db_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def request_hash(body: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> str:
    """Deterministic hash of request body (and optional extra keys) for idempotency."""
    data = dict(body) if body else {}
    if extra:
        data = {**data, **extra}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def effects_hash(tool_name: str, inputs: Dict[str, Any], target: str = "") -> str:
    """Hash for tool side-effect dedupe: tool_name + canonical inputs + target."""
    canonical = json.dumps(
        {"tool_name": tool_name, "inputs": inputs or {}, "target": target},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_idempotency(
    tenant_id: str,
    idempotency_key: str,
    db_path: Optional[str] = None,
) -> Optional[Tuple[str, str, int]]:
    """Return (request_hash, response_body, response_status) if record exists, else None."""
    path = db_path or _get_db_path()
    try:
        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT request_hash, response_body, response_status FROM idempotency_records WHERE tenant_id = ? AND idempotency_key = ?",
                (tenant_id, idempotency_key),
            ).fetchone()
            if not row:
                return None
            return (row["request_hash"], row["response_body"], row["response_status"])
    except Exception:
        return None


def set_idempotency(
    tenant_id: str,
    idempotency_key: str,
    route: str,
    request_hash_val: str,
    response_body: str,
    response_status: int = 200,
    db_path: Optional[str] = None,
) -> None:
    """Store idempotency record. Overwrites if same key (first write wins for same key+hash)."""
    path = db_path or _get_db_path()
    now = _now()
    with get_connection(path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO idempotency_records
               (tenant_id, idempotency_key, route, request_hash, response_body, response_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tenant_id, idempotency_key, route, request_hash_val, response_body, response_status, now),
        )


def get_tool_effect(tenant_id: str, effects_hash_val: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return cached tool result dict if present."""
    path = db_path or _get_db_path()
    try:
        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT result_json FROM tool_effect_ledger WHERE tenant_id = ? AND effects_hash = ?",
                (tenant_id, effects_hash_val),
            ).fetchone()
            if not row or not row["result_json"]:
                return None
            return json.loads(row["result_json"])
    except Exception:
        return None


def set_tool_effect(
    tenant_id: str,
    effects_hash_val: str,
    result: Dict[str, Any],
    db_path: Optional[str] = None,
) -> None:
    """Store tool result for effects_hash (dedupe)."""
    path = db_path or _get_db_path()
    now = _now()
    with get_connection(path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO tool_effect_ledger (tenant_id, effects_hash, result_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (tenant_id, effects_hash_val, json.dumps(result), now),
        )
