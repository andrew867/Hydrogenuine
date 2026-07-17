"""
Interop Pack 4: Trust root rotation and compromise response.
BRIDGE_TRUST_ROOT_PUBLISHED, BRIDGE_TRUST_ROOT_ROTATED (via threshold), GRANTS_FROZEN, COMPROMISE_RESPONSE_RECORDED.
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


def publish_bridge_trust_root(
    *,
    bridge_id: str,
    root_version: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    artifact_ref: Optional[str] = None,
) -> str:
    """Publish bridge trust root version. Emit BRIDGE_TRUST_ROOT_PUBLISHED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "trust_roots" / "bridges"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{bridge_id}_{root_version}.json"
    path.write_text(json.dumps({"bridge_id": bridge_id, "root_version": root_version, "ts": ts}, indent=2), encoding="utf-8")
    return emit(
        "BRIDGE_TRUST_ROOT_PUBLISHED",
        "trust_root",
        f"{bridge_id}:{root_version}",
        {"bridge_id": bridge_id, "root_version": root_version, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def rotate_bridge_trust_root(
    *,
    bridge_id: str,
    new_root_version: str,
    threshold_action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Record bridge trust root rotation (after threshold). Emit BRIDGE_TRUST_ROOT_ROTATED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "BRIDGE_TRUST_ROOT_ROTATED",
        "trust_root",
        bridge_id,
        {"bridge_id": bridge_id, "new_root_version": new_root_version, "threshold_action_id": threshold_action_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def freeze_grants_on_compromise(
    *,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    incident_ref: Optional[str] = None,
) -> str:
    """Freeze grants on compromise. Emit GRANTS_FROZEN. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"reason": reason, "ts": ts}
    if incident_ref:
        payload["incident_ref"] = incident_ref
    return emit(
        "GRANTS_FROZEN",
        "compromise_response",
        "freeze_" + hashlib.sha256(ts.encode()).hexdigest()[:12],
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_compromise_response(
    *,
    response_type: str,
    details: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Record compromise response (key rotation, tier raise, etc.). Emit COMPROMISE_RESPONSE_RECORDED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    resp_id = "comp_" + hashlib.sha256(f"{response_type}:{ts}".encode()).hexdigest()[:12]
    root = workspace_root / "artifacts" / "compromise_responses"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{resp_id}.json"
    path.write_text(json.dumps({"response_id": resp_id, "response_type": response_type, "details": details, "ts": ts}, indent=2), encoding="utf-8")
    return emit(
        "COMPROMISE_RESPONSE_RECORDED",
        "compromise_response",
        resp_id,
        {"response_id": resp_id, "response_type": response_type, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
