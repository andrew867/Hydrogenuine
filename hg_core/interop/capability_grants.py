"""
Interop Pack 1: Capability grants — short-lived scoped permissions, revocable, auditable.
CAPABILITY_GRANT_ISSUED, CAPABILITY_GRANT_USED, CAPABILITY_GRANT_REVOKED, CAPABILITY_GRANT_EXPIRED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def issue_capability_grant(
    *,
    subject: Dict[str, str],
    resource: Dict[str, Any],
    scope: Dict[str, str],
    expires_ts: str,
    scope_ledger: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    policy_proof_id: Optional[str] = None,
) -> str:
    """Write grant artifact, emit CAPABILITY_GRANT_ISSUED. Returns grant_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    grant_id = "cg_" + hashlib.sha256(f"{subject.get('id','')}:{resource.get('connector_id','')}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "capability_grants"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{grant_id}.json"
    doc = {
        "grant_id": grant_id,
        "subject": subject,
        "resource": resource,
        "scope": scope,
        "issued_ts": ts,
        "expires_ts": expires_ts,
        "policy_proof_id": policy_proof_id,
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "CAPABILITY_GRANT_ISSUED",
        "capability_grant",
        grant_id,
        {"grant_id": grant_id, "artifact_id": str(path), "expires_ts": expires_ts, "ts": ts},
        scope=scope_ledger,
        actor=actor,
        workspace_root=workspace_root,
    )
    return grant_id


def validate_grant(grant: Dict[str, Any], now_ts: str) -> bool:
    """Return True if grant is valid: not expired, not revoked, required fields present."""
    if not grant:
        return False
    exp = grant.get("expires_ts")
    if not exp or exp <= now_ts:
        return False
    if grant.get("revoked_ts"):
        return False
    if not grant.get("subject") or not grant.get("resource") or not grant.get("scope"):
        return False
    return True


def revoke_capability_grant(
    *,
    grant_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Update grant artifact with revoked_ts, emit CAPABILITY_GRANT_REVOKED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    path = workspace_root / "artifacts" / "capability_grants" / f"{grant_id}.json"
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc["revoked_ts"] = ts
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass
    return emit(
        "CAPABILITY_GRANT_REVOKED",
        "capability_grant",
        grant_id,
        {"grant_id": grant_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_grant_used(
    *,
    grant_id: str,
    call_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit CAPABILITY_GRANT_USED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "CAPABILITY_GRANT_USED",
        "capability_grant",
        grant_id,
        {"grant_id": grant_id, "call_id": call_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def load_grant(workspace_root: Path, grant_id: str) -> Optional[Dict[str, Any]]:
    """Load grant from artifacts/capability_grants/{grant_id}.json."""
    path = workspace_root / "artifacts" / "capability_grants" / f"{grant_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def emit_grant_expired_if_needed(
    *,
    grant_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Optional[str]:
    """If grant exists and is expired (and not already revoked), emit CAPABILITY_GRANT_EXPIRED. Returns event_id or None."""
    workspace_root = Path(workspace_root or ".")
    grant = load_grant(workspace_root, grant_id)
    if not grant or grant.get("revoked_ts"):
        return None
    now = _iso_ts()
    if not grant.get("expires_ts") or grant["expires_ts"] > now:
        return None
    ts = _iso_ts()
    return emit(
        "CAPABILITY_GRANT_EXPIRED",
        "capability_grant",
        grant_id,
        {"grant_id": grant_id, "expires_ts": grant["expires_ts"], "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
