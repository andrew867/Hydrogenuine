from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection


def _gateway_db_path(workspace_root: Path) -> str | None:
    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    try:
        return str((workspace_root / "memory" / "gateway.sqlite3").resolve())
    except Exception:
        return None


def _load_payload(raw: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        payload = {}
    return payload if isinstance(payload, dict) else {}


def load_operational_json_state(
    workspace_root: Path | None,
    *,
    state_key: str,
    legacy_path: Path | None = None,
) -> dict[str, Any]:
    if workspace_root is not None:
        db_path = _gateway_db_path(workspace_root)
        if db_path:
            try:
                with get_connection(db_path) as conn:
                    row = conn.execute(
                        "SELECT payload, updated_at FROM operational_state WHERE state_key = ?",
                        (state_key,),
                    ).fetchone()
                if row:
                    payload_raw = row[0] if not isinstance(row, dict) else row.get("payload")
                    return {
                        "present": True,
                        "payload": _load_payload(payload_raw),
                        "source": "db",
                        "updated_at": row[1] if not isinstance(row, dict) else row.get("updated_at"),
                        "path": str(legacy_path) if legacy_path else None,
                    }
            except Exception:
                pass

    return {
        "present": False,
        "payload": {},
        "source": None,
        "updated_at": None,
        "path": str(legacy_path) if legacy_path else None,
    }


def save_operational_json_state(
    workspace_root: Path,
    *,
    state_key: str,
    payload: dict[str, Any],
    legacy_path: Path | None = None,
) -> dict[str, Any]:
    db_path = _gateway_db_path(workspace_root)
    if db_path:
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO operational_state (state_key, payload, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (state_key, json.dumps(payload, ensure_ascii=False)),
                )
        except Exception:
            pass
    return load_operational_json_state(workspace_root, state_key=state_key, legacy_path=legacy_path)
