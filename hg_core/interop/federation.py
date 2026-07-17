"""
Interop Pack 2: Federation — multi-domain links, policy application, violation detection.
FEDERATION_LINK_PROPOSED, FEDERATION_LINK_ACCEPTED, FEDERATION_LINK_REJECTED,
FEDERATION_POLICY_APPLIED, FEDERATION_VIOLATION_DETECTED.
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


def propose_federation_link(
    *,
    domains: List[str],
    rules: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    expires_ts: Optional[str] = None,
) -> str:
    """Write link artifact, emit FEDERATION_LINK_PROPOSED. Returns link_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    link_id = "flink_" + hashlib.sha256(f"{':'.join(domains)}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "federation"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{link_id}.json"
    doc = {"link_id": link_id, "domains": domains, "rules": rules, "ts": ts, "expires_ts": expires_ts or ""}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "FEDERATION_LINK_PROPOSED",
        "federation_link",
        link_id,
        {"link_id": link_id, "artifact_id": str(path), "domains": domains, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return link_id


def accept_federation_link(
    *,
    link_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit FEDERATION_LINK_ACCEPTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "FEDERATION_LINK_ACCEPTED",
        "federation_link",
        link_id,
        {"link_id": link_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def reject_federation_link(
    *,
    link_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit FEDERATION_LINK_REJECTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "FEDERATION_LINK_REJECTED",
        "federation_link",
        link_id,
        {"link_id": link_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def apply_federation_policy(
    *,
    link_id: str,
    exchange_type: str,
    ref_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit FEDERATION_POLICY_APPLIED (per A2A exchange or connector call). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "FEDERATION_POLICY_APPLIED",
        "federation_link",
        link_id,
        {"link_id": link_id, "exchange_type": exchange_type, "ref_id": ref_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def emit_federation_violation(
    *,
    link_id: str,
    reason: str,
    ref_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit FEDERATION_VIOLATION_DETECTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "FEDERATION_VIOLATION_DETECTED",
        "federation_link",
        link_id,
        {"link_id": link_id, "reason": reason, "ref_id": ref_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def load_federation_link(workspace_root: Path, link_id: str) -> Optional[Dict[str, Any]]:
    """Load federation link from artifacts/federation/{link_id}.json."""
    path = workspace_root / "artifacts" / "federation" / f"{link_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def validate_cross_domain_a2a(workspace_root: Path, link_id: str, message_scope: Dict[str, str], now_ts: str) -> tuple:
    """Return (valid, reason). Cross-domain A2A must reference a valid accepted link."""
    link = load_federation_link(workspace_root, link_id)
    if not link:
        return False, "no_federation_link"
    if link.get("expires_ts") and link["expires_ts"] and link["expires_ts"] <= now_ts:
        return False, "link_expired"
    return True, "ok"
