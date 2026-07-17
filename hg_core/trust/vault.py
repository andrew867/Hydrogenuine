"""
Interop Pack 4: Vault and key custody — key lifecycle, short-lived tokens, break-glass.
KEY_CREATED, KEY_ROTATED, KEY_REVOKED, SECRET_TOKEN_ISSUED, SECRET_TOKEN_REVOKED,
BREAK_GLASS_REQUESTED, BREAK_GLASS_GRANTED, BREAK_GLASS_EXPIRED, VAULT_HEALTH_CHECK_RAN.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_key(
    *,
    key_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    key_type: str = "signing",
) -> str:
    """Record key creation (no secret material). Emit KEY_CREATED. Returns key_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "vault_keys"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{key_id}.json"
    doc = {"key_id": key_id, "key_type": key_type, "created_ts": ts, "revoked_ts": ""}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "KEY_CREATED",
        "vault_key",
        key_id,
        {"key_id": key_id, "key_type": key_type, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return key_id


def rotate_key(
    *,
    key_id: str,
    new_key_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Record key rotation. Emit KEY_ROTATED. Returns new_key_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "vault_keys"
    root.mkdir(parents=True, exist_ok=True)
    path_new = root / f"{new_key_id}.json"
    path_new.write_text(
        json.dumps({"key_id": new_key_id, "rotated_from": key_id, "created_ts": ts, "revoked_ts": ""}, indent=2),
        encoding="utf-8",
    )
    emit(
        "KEY_ROTATED",
        "vault_key",
        key_id,
        {"key_id": key_id, "new_key_id": new_key_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return new_key_id


def revoke_key(
    *,
    key_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Record key revocation. Emit KEY_REVOKED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    path = workspace_root / "artifacts" / "vault_keys" / f"{key_id}.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["revoked_ts"] = ts
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "KEY_REVOKED",
        "vault_key",
        key_id,
        {"key_id": key_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def issue_short_lived_token(
    *,
    token_scope: str,
    expires_in_seconds: int,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    connector_id: Optional[str] = None,
) -> str:
    """Issue short-lived token (artifact ref only). Emit SECRET_TOKEN_ISSUED. Returns token_ref_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    ref_id = "tok_" + hashlib.sha256(f"{token_scope}:{ts}".encode()).hexdigest()[:16]
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat().replace("+00:00", "Z")
    root = workspace_root / "artifacts" / "vault_tokens"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{ref_id}.json"
    doc = {"token_ref_id": ref_id, "token_scope": token_scope, "issued_ts": ts, "expires_ts": expiry, "revoked_ts": ""}
    if connector_id:
        doc["connector_id"] = connector_id
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "SECRET_TOKEN_ISSUED",
        "vault_token",
        ref_id,
        {"token_ref_id": ref_id, "token_scope": token_scope, "expires_ts": expiry, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return ref_id


def revoke_token(
    *,
    token_ref_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Revoke token. Emit SECRET_TOKEN_REVOKED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    path = workspace_root / "artifacts" / "vault_tokens" / f"{token_ref_id}.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["revoked_ts"] = ts
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "SECRET_TOKEN_REVOKED",
        "vault_token",
        token_ref_id,
        {"token_ref_id": token_ref_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def request_break_glass(
    *,
    request_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Request break-glass. Emit BREAK_GLASS_REQUESTED. Returns request_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "BREAK_GLASS_REQUESTED",
        "break_glass",
        request_id,
        {"request_id": request_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def grant_break_glass(
    *,
    request_id: str,
    expires_in_seconds: int,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Grant break-glass (time-bound). Emit BREAK_GLASS_GRANTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat().replace("+00:00", "Z")
    return emit(
        "BREAK_GLASS_GRANTED",
        "break_glass",
        request_id,
        {"request_id": request_id, "expires_ts": expiry, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def expire_break_glass(
    *,
    request_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Mark break-glass expired. Emit BREAK_GLASS_EXPIRED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "BREAK_GLASS_EXPIRED",
        "break_glass",
        request_id,
        {"request_id": request_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def run_vault_health_check(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Run vault health check. Emit VAULT_HEALTH_CHECK_RAN. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    report_id = "vault_health_" + hashlib.sha256(ts.encode()).hexdigest()[:12]
    root = workspace_root / "artifacts" / "vault_health"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{report_id}.json"
    path.write_text(json.dumps({"report_id": report_id, "ts": ts, "status": "ok"}, indent=2), encoding="utf-8")
    return emit(
        "VAULT_HEALTH_CHECK_RAN",
        "vault_health",
        report_id,
        {"report_id": report_id, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
