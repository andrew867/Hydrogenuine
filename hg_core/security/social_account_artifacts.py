"""Helpers for persisting proof artifacts directly against social accounts."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from hg_gateway.db import _get_db_path, get_connection


def account_artifacts_root() -> Path:
    """Root directory for persisted social-account proof artifacts."""
    return Path("memory/artifacts/social_accounts").expanduser().resolve()


def write_social_account_artifact(
    social_account_id: str,
    *,
    label: str,
    payload: dict[str, Any],
) -> str:
    """Write a JSON artifact payload for a social account and return the path."""
    root = account_artifacts_root() / social_account_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{label}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def register_social_account_artifact(
    social_account_id: str,
    *,
    artifact_type: str,
    path: str,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Register a proof artifact row for a social account."""
    proof_id = str(uuid.uuid4())
    with get_connection(_get_db_path()) as conn:
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'social_account', ?, ?, ?, ?, datetime('now'))""",
            (proof_id, social_account_id, artifact_type, path, json.dumps(metadata or {})),
        )
    return {
        "proof_id": proof_id,
        "artifact_type": artifact_type,
        "path": path,
        "metadata": metadata or {},
    }


def record_social_account_artifact(
    social_account_id: str,
    *,
    artifact_type: str,
    label: str,
    payload: dict[str, Any],
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Write and register a proof artifact directly against a social account."""
    path = write_social_account_artifact(
        social_account_id,
        label=label,
        payload=payload,
    )
    return register_social_account_artifact(
        social_account_id,
        artifact_type=artifact_type,
        path=path,
        metadata=metadata,
    )


def record_social_account_session_binding(
    social_account_id: str,
    *,
    browser_session_id: str,
    platform: str,
    tenant_id: str,
    entity_id: str,
    account_alias: Optional[str] = None,
    state: Optional[str] = None,
) -> dict[str, Any]:
    """Persist an explicit social-account to browser-session binding artifact."""
    payload = {
        "social_account_id": social_account_id,
        "browser_session_id": browser_session_id,
        "platform": platform,
        "tenant_id": tenant_id,
        "entity_id": entity_id,
        "account_alias": account_alias,
        "state": state,
    }
    return record_social_account_artifact(
        social_account_id,
        artifact_type="browser_session_binding",
        label=f"browser-session-{browser_session_id}",
        payload=payload,
        metadata={
            "browser_session_id": browser_session_id,
            "platform": platform,
            "entity_id": entity_id,
            "account_alias": account_alias,
            "state": state,
        },
    )


def get_latest_bound_browser_session_id(social_account_id: str) -> Optional[str]:
    """Return the most recent browser session explicitly bound to a social account."""
    with get_connection(_get_db_path()) as conn:
        row = conn.execute(
            """SELECT path, metadata_json
               FROM proof_artifacts
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding'
               ORDER BY created_at DESC, proof_id DESC
               LIMIT 1""",
            (social_account_id,),
        ).fetchone()
    if not row:
        return None
    path, metadata_json = row
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8")) if path and Path(path).exists() else {}
    except Exception:
        payload = {}
    metadata = json.loads(metadata_json) if metadata_json else {}
    session_id = (payload.get("browser_session_id") or metadata.get("browser_session_id") or "").strip()
    return session_id or None
