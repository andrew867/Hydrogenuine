"""
Interop Pack 4: Issuer governance — issuer groups, quorum, VC issuance/revocation proposals.
ISSUER_GROUP_PUBLISHED, ISSUER_GROUP_MEMBER_ADDED, ISSUER_GROUP_MEMBER_REMOVED,
VC_ISSUANCE_PROPOSED, VC_REVOCATION_PROPOSED.
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


def publish_issuer_group(
    *,
    group_id: str,
    members: List[str],
    quorum_m: int,
    quorum_n: int,
    permitted_types: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    expires_ts: Optional[str] = None,
) -> str:
    """Publish issuer group. Emit ISSUER_GROUP_PUBLISHED. Returns group_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    doc = {
        "group_id": group_id,
        "members": list(members),
        "quorum": {"m": quorum_m, "n": quorum_n},
        "permitted_types": list(permitted_types),
        "ts": ts,
    }
    if expires_ts:
        doc["expires_ts"] = expires_ts
    root = workspace_root / "artifacts" / "issuer_groups"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{group_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "ISSUER_GROUP_PUBLISHED",
        "issuer_group",
        group_id,
        {"group_id": group_id, "artifact_id": str(path), "quorum": doc["quorum"], "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return group_id


def add_issuer_group_member(
    *,
    group_id: str,
    member_did: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Add member to issuer group. Emit ISSUER_GROUP_MEMBER_ADDED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    path = workspace_root / "artifacts" / "issuer_groups" / f"{group_id}.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        members = doc.get("members") or []
        if member_did not in members:
            members.append(member_did)
            doc["members"] = members
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "ISSUER_GROUP_MEMBER_ADDED",
        "issuer_group",
        group_id,
        {"group_id": group_id, "member_did": member_did, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def remove_issuer_group_member(
    *,
    group_id: str,
    member_did: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Remove member from issuer group. Emit ISSUER_GROUP_MEMBER_REMOVED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    path = workspace_root / "artifacts" / "issuer_groups" / f"{group_id}.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        members = doc.get("members") or []
        if member_did in members:
            doc["members"] = [m for m in members if m != member_did]
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "ISSUER_GROUP_MEMBER_REMOVED",
        "issuer_group",
        group_id,
        {"group_id": group_id, "member_did": member_did, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def load_issuer_group(workspace_root: Path, group_id: str) -> Optional[Dict[str, Any]]:
    """Load issuer group by group_id. Returns None if not found."""
    path = workspace_root / "artifacts" / "issuer_groups" / f"{group_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def check_issuer_quorum_for_type(
    workspace_root: Path,
    group_id: str,
    credential_type: str,
) -> tuple:
    """Check if group has quorum and permits credential_type. Returns (allowed: bool, reason: str)."""
    group = load_issuer_group(workspace_root, group_id)
    if not group:
        return False, "group_not_found"
    permitted = group.get("permitted_types") or []
    if credential_type not in permitted:
        return False, "type_not_permitted"
    quorum = group.get("quorum") or {}
    m, n = quorum.get("m", 0), quorum.get("n", 0)
    members = group.get("members") or []
    if n > 0 and len(members) < n:
        return False, "insufficient_members"
    return True, ""


def propose_vc_issuance(
    *,
    group_id: str,
    credential_type: str,
    payload_ref: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    expires_ts: Optional[str] = None,
) -> str:
    """Propose VC issuance as threshold action. Emit VC_ISSUANCE_PROPOSED (and create threshold action). Returns action_id."""
    workspace_root = Path(workspace_root or ".")
    group = load_issuer_group(workspace_root, group_id)
    if not group:
        raise ValueError(f"issuer group not found: {group_id}")
    quorum = group.get("quorum") or {}
    m, n = quorum.get("m", 1), quorum.get("n", 1)
    from hg_core.trust.threshold import propose_threshold_action
    action_id = propose_threshold_action(
        action_type="VC_ISSUANCE",
        scope=scope,
        quorum_m=m,
        quorum_n=n,
        payload_ref={"group_id": group_id, "credential_type": credential_type, **payload_ref},
        actor=actor,
        workspace_root=workspace_root,
        expires_ts=expires_ts,
    )
    ts = _iso_ts()
    emit(
        "VC_ISSUANCE_PROPOSED",
        "threshold_action",
        action_id,
        {"action_id": action_id, "group_id": group_id, "credential_type": credential_type, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return action_id


def propose_vc_revocation(
    *,
    group_id: str,
    vc_id: str,
    payload_ref: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    expires_ts: Optional[str] = None,
) -> str:
    """Propose VC revocation as threshold action. Emit VC_REVOCATION_PROPOSED. Returns action_id."""
    workspace_root = Path(workspace_root or ".")
    group = load_issuer_group(workspace_root, group_id)
    if not group:
        raise ValueError(f"issuer group not found: {group_id}")
    quorum = group.get("quorum") or {}
    m, n = quorum.get("m", 1), quorum.get("n", 1)
    from hg_core.trust.threshold import propose_threshold_action
    action_id = propose_threshold_action(
        action_type="VC_REVOCATION",
        scope=scope,
        quorum_m=m,
        quorum_n=n,
        payload_ref={"group_id": group_id, "vc_id": vc_id, **payload_ref},
        actor=actor,
        workspace_root=workspace_root,
        expires_ts=expires_ts,
    )
    ts = _iso_ts()
    emit(
        "VC_REVOCATION_PROPOSED",
        "threshold_action",
        action_id,
        {"action_id": action_id, "group_id": group_id, "vc_id": vc_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return action_id
