"""
Interop Pack 4: Threshold signing — M-of-N for trust actions.
THRESHOLD_ACTION_PROPOSED, THRESHOLD_SIGNATURE_ADDED, THRESHOLD_ACTION_FINALIZED, THRESHOLD_ACTION_EXPIRED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def propose_threshold_action(
    *,
    action_type: str,
    scope: Dict[str, str],
    quorum_m: int,
    quorum_n: int,
    payload_ref: Dict[str, Any],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    expires_ts: Optional[str] = None,
) -> str:
    """Create threshold action artifact and emit THRESHOLD_ACTION_PROPOSED. Returns action_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    action_id = "tact_" + hashlib.sha256(f"{action_type}:{ts}".encode()).hexdigest()[:16]
    exp = expires_ts or ""
    doc = {
        "action_id": action_id,
        "action_type": action_type,
        "scope": scope,
        "proposed_ts": ts,
        "expires_ts": exp,
        "quorum": {"m": quorum_m, "n": quorum_n},
        "payload_ref": payload_ref,
        "signatures": [],
    }
    root = workspace_root / "artifacts" / "threshold_actions"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{action_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "THRESHOLD_ACTION_PROPOSED",
        "threshold_action",
        action_id,
        {"action_id": action_id, "action_type": action_type, "artifact_id": str(path), "quorum": doc["quorum"], "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return action_id


def load_threshold_action(workspace_root: Path, action_id: str) -> Optional[Dict[str, Any]]:
    """Load threshold action by action_id. Returns None if not found."""
    path = workspace_root / "artifacts" / "threshold_actions" / f"{action_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def add_threshold_signature(
    *,
    action_id: str,
    signer_id: str,
    signature_payload: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    disallowed_signer_ids: Optional[Set[str]] = None,
) -> tuple:
    """
    Add a signature to the threshold action. Enforces signer independence (no duplicate, not in disallowed).
    Returns (added: bool, event_id: str, reason: Optional[str]).
    """
    workspace_root = Path(workspace_root or ".")
    action = load_threshold_action(workspace_root, action_id)
    if not action:
        return False, "", "action_not_found"
    if action.get("finalized_ts"):
        return False, "", "already_finalized"
    exp = action.get("expires_ts")
    now = _iso_ts()
    if exp and exp < now:
        emit(
            "THRESHOLD_ACTION_EXPIRED",
            "threshold_action",
            action_id,
            {"action_id": action_id, "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, "", "expired"
    disallowed = disallowed_signer_ids or set()
    if signer_id in disallowed:
        return False, "", "signer_independence"
    sigs = action.get("signatures") or []
    for s in sigs:
        if s.get("signer_id") == signer_id:
            return False, "", "duplicate_signer"
    sig_entry = {"signer_id": signer_id, "signature_payload": signature_payload, "ts": now}
    sigs.append(sig_entry)
    action["signatures"] = sigs
    path = workspace_root / "artifacts" / "threshold_actions" / f"{action_id}.json"
    path.write_text(json.dumps(action, indent=2), encoding="utf-8")
    ev = emit(
        "THRESHOLD_SIGNATURE_ADDED",
        "threshold_action",
        action_id,
        {"action_id": action_id, "signer_id": signer_id, "ts": now},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, ev, None


def finalize_threshold_action(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> tuple:
    """
    Finalize when quorum reached. Emit THRESHOLD_ACTION_FINALIZED with signatures artifact ref, or THRESHOLD_ACTION_EXPIRED if expired.
    Returns (finalized: bool, event_id: str, reason: Optional[str]).
    """
    workspace_root = Path(workspace_root or ".")
    action = load_threshold_action(workspace_root, action_id)
    if not action:
        return False, "", "action_not_found"
    if action.get("finalized_ts"):
        return False, "", "already_finalized"
    now = _iso_ts()
    exp = action.get("expires_ts")
    if exp and exp < now:
        ev = emit(
            "THRESHOLD_ACTION_EXPIRED",
            "threshold_action",
            action_id,
            {"action_id": action_id, "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "expired"
    quorum = action.get("quorum") or {}
    m, n = quorum.get("m", 0), quorum.get("n", 0)
    sigs = action.get("signatures") or []
    if len(sigs) < m:
        return False, "", "quorum_not_reached"
    action["finalized_ts"] = now
    sig_root = workspace_root / "artifacts" / "threshold_signatures"
    sig_root.mkdir(parents=True, exist_ok=True)
    sig_path = sig_root / f"{action_id}.json"
    sig_path.write_text(json.dumps({"action_id": action_id, "signatures": sigs, "ts": now}, indent=2), encoding="utf-8")
    path = workspace_root / "artifacts" / "threshold_actions" / f"{action_id}.json"
    path.write_text(json.dumps(action, indent=2), encoding="utf-8")
    ev = emit(
        "THRESHOLD_ACTION_FINALIZED",
        "threshold_action",
        action_id,
        {"action_id": action_id, "signatures_artifact_id": str(sig_path), "ts": now},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, ev, None
