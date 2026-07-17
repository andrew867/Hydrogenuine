"""
Interop Pack 2: DID/VC identity — DID registry, VC issuance/revocation, trust roots.
DID_REGISTERED, VC_ISSUED, VC_REVOKED, VC_EXPIRED (derived), IDENTITY_TRUST_ROOT_PUBLISHED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def register_did(
    *,
    did: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    document: Optional[Dict[str, Any]] = None,
) -> str:
    """Write DID artifact, emit DID_REGISTERED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "identity" / "dids"
    root.mkdir(parents=True, exist_ok=True)
    safe_id = did.replace(":", "_")[:64]
    path = root / f"{safe_id}.json"
    doc = {"did": did, "registered_ts": ts, "document": document or {}}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "DID_REGISTERED",
        "identity",
        did,
        {"did": did, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def issue_vc(
    *,
    issuer: str,
    subject_did: str,
    claims: Dict[str, Any],
    expires_ts: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Write VC artifact, emit VC_ISSUED. Returns vc_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    vc_id = "vc_" + hashlib.sha256(f"{issuer}:{subject_did}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "identity" / "vcs"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{vc_id}.json"
    doc = {
        "vc_id": vc_id,
        "issuer": issuer,
        "subject_did": subject_did,
        "claims": claims,
        "issued_ts": ts,
        "expires_ts": expires_ts,
        "signature": {"alg": "sha256_hex", "value": hashlib.sha256(json.dumps(claims, sort_keys=True).encode()).hexdigest()[:32]},
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "VC_ISSUED",
        "verifiable_credential",
        vc_id,
        {"vc_id": vc_id, "issuer": issuer, "subject_did": subject_did, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return vc_id


def revoke_vc(
    *,
    vc_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Update VC with revoked_ts, emit VC_REVOKED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "identity" / "vcs"
    path = root / f"{vc_id}.json"
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc["revoked_ts"] = ts
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass
    return emit(
        "VC_REVOKED",
        "verifiable_credential",
        vc_id,
        {"vc_id": vc_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def load_vc(workspace_root: Path, vc_id: str) -> Optional[Dict[str, Any]]:
    """Load VC from artifacts/identity/vcs/{vc_id}.json."""
    path = workspace_root / "artifacts" / "identity" / "vcs" / f"{vc_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def validate_vc(vc: Dict[str, Any], now_ts: str) -> tuple[bool, str]:
    """Return (valid, reason). Invalid/revoked VC blocks privileged intent."""
    if not vc:
        return False, "no_vc"
    if vc.get("revoked_ts"):
        return False, "revoked"
    exp = vc.get("expires_ts")
    if not exp or exp <= now_ts:
        return False, "expired"
    return True, "ok"


def publish_trust_root(
    *,
    root_id: str,
    domain: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    allowed_issuers: Optional[List[str]] = None,
) -> str:
    """Write trust root artifact, emit IDENTITY_TRUST_ROOT_PUBLISHED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "identity" / "trust_roots"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{root_id}.json"
    doc = {"root_id": root_id, "domain": domain, "allowed_issuers": allowed_issuers or [], "ts": ts}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "IDENTITY_TRUST_ROOT_PUBLISHED",
        "identity",
        root_id,
        {"root_id": root_id, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
