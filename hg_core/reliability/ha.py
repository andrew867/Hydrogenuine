"""
HA/DR: health status (ledger ok, materializer lag, last backup), backup completion recording.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_gateway.artifact_registry import upsert_artifact_record
from hg_gateway.db import get_connection
from hg_core.ledger.ledger_verify import verify_chain
from hg_core.observability.metrics import get_metrics


BACKUP_MARKER_REL_PATH = "artifacts/backups/last_backup.json"


def _backup_marker_ts_from_registry(workspace_root: Path) -> Optional[str]:
    db_path = workspace_root / "memory" / "gateway.sqlite3"
    try:
        with get_connection(str(db_path)) as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM artifact_registry_entries
                WHERE class_key = ? AND file_path = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                ("backup", BACKUP_MARKER_REL_PATH),
            ).fetchone()
            if not row:
                return None
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
            if isinstance(payload, dict):
                ts = payload.get("ts")
                return str(ts) if ts else None
    except Exception:
        return None
    return None


def get_ha_status(workspace_root: Path) -> Dict[str, Any]:
    """
    Return HA status: ledger_ok (from verify_chain), materializer_lag_seconds (max lag from metrics),
    last_backup_ts (from artifacts/backups/last_backup.json if present), metrics snapshot.
    """
    workspace_root = Path(workspace_root)
    out: Dict[str, Any] = {"ledger_ok": False, "materializer_lag_seconds": None, "last_backup_ts": None, "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    try:
        result = verify_chain(workspace_root)
        out["ledger_ok"] = result.get("ok", False)
    except Exception:
        out["ledger_ok"] = False
    metrics = get_metrics()
    lag_ts = metrics.get("materializer_last_lag_ts") or {}
    if lag_ts:
        out["materializer_lag_seconds"] = max(lag_ts.values()) if lag_ts else None
    backup_ts = _backup_marker_ts_from_registry(workspace_root)
    if backup_ts:
        out["last_backup_ts"] = backup_ts
    backup_file = workspace_root / "artifacts" / "backups" / "last_backup.json"
    if out["last_backup_ts"] is None and backup_file.exists():
        try:
            data = json.loads(backup_file.read_text(encoding="utf-8"))
            out["last_backup_ts"] = data.get("ts")
        except Exception:
            pass
    out["metrics"] = metrics
    return out


def record_backup_completed(workspace_root: Path, backup_id: Optional[str] = None) -> None:
    """Write artifacts/backups/last_backup.json and register the backup marker in the gateway DB."""
    root = workspace_root / "artifacts" / "backups"
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path = root / "last_backup.json"
    payload = {"ts": ts, "backup_id": backup_id or ""}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        with get_connection(str(workspace_root / "memory" / "gateway.sqlite3")) as conn:
            upsert_artifact_record(
                conn,
                file_path=path.relative_to(workspace_root).as_posix(),
                class_key="backup",
                title="Last backup marker",
                content_kind="backup_marker",
                actor_id="system",
                change_summary="record backup completed",
                root=workspace_root,
            )
    except Exception:
        pass
