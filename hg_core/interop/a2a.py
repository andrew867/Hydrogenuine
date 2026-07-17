# Interop Pack 1: A2A envelope
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit

def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def validate_envelope(env: Dict[str, Any], now_ts: str) -> Dict[str, Any]:
    if not env:
        return {"ok": False, "reason": "empty_envelope"}
    exp = env.get("expires_ts")
    if not exp or exp <= now_ts:
        return {"ok": False, "reason": "expired"}
    if not env.get("message_id") or not env.get("from") or not env.get("to") or not env.get("scope"):
        return {"ok": False, "reason": "missing_required_fields"}
    if not env.get("integrity"):
        return {"ok": False, "reason": "missing_integrity"}
    return {"ok": True}

def send_a2a_message(*, from_agent: Dict[str, Any], to_agent: Dict[str, Any], scope: Dict[str, str], body: Dict[str, Any], scope_ledger: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None, expires_ts: Optional[str] = None, attachments: Optional[list] = None) -> tuple:
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    exp = expires_ts or ts
    message_id = "a2a_" + hashlib.sha256(f"{ts}:{scope.get('id','')}".encode()).hexdigest()[:16]
    integrity = {"hash": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:32]}
    envelope = {"message_id": message_id, "from": from_agent, "to": to_agent, "scope": scope, "ts": ts, "expires_ts": exp, "body": body, "integrity": integrity, "attachments": attachments or []}
    root = workspace_root / "artifacts" / "a2a"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{message_id}.json"
    path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    ev_id = emit("A2A_MESSAGE_SENT", "a2a_message", message_id, {"message_id": message_id, "artifact_id": str(path), "ts": ts, "expires_ts": exp}, scope=scope_ledger, actor=actor, workspace_root=workspace_root)
    return message_id, ev_id

def receive_a2a_message(*, message_id: str, envelope: Dict[str, Any], scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> tuple:
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    val = validate_envelope(envelope, ts)
    if not val.get("ok"):
        ev_id = emit("A2A_MESSAGE_REJECTED", "a2a_message", message_id, {"message_id": message_id, "reason": val.get("reason", "invalid"), "ts": ts}, scope=scope, actor=actor, workspace_root=workspace_root)
        return False, ev_id
    ev_id = emit("A2A_MESSAGE_RECEIVED", "a2a_message", message_id, {"message_id": message_id, "ts": ts}, scope=scope, actor=actor, workspace_root=workspace_root)
    return True, ev_id
