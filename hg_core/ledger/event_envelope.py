"""
Ledger event envelope: build and validate event_id (hash of canonical body), sign, verify.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .canonical_json import canonical_dumps
from .crypto import sign, verify


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def body_for_hash(event: Dict[str, Any]) -> Dict[str, Any]:
    """Return the dict that is hashed for event_id (exclude sig; include prev_hash, actor, ts, scope, action, object, payload)."""
    return {
        "prev_hash": event.get("prev_hash"),
        "actor": event.get("actor"),
        "ts": event.get("ts"),
        "scope": event.get("scope"),
        "action": event.get("action"),
        "object": event.get("object"),
        "payload": event.get("payload"),
    }


def compute_event_id(body: Dict[str, Any]) -> str:
    """Compute event_id as SHA-256 hex of canonical JSON of body (prev_hash, actor, ts, scope, action, object, payload)."""
    raw = canonical_dumps(body)
    return hashlib.sha256(raw).hexdigest()


def build_envelope(
    action: str,
    object_type: str,
    object_id: str,
    payload: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    prev_hash: Optional[str] = None,
    ts: Optional[str] = None,
    object_path: Optional[str] = None,
    secret_key_hex: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a full ledger event envelope. Computes event_id and optionally signs.
    scope: {"type": "run"|"session"|"cycle"|"global", "id": "<id>"}
    actor: {"agent_id": str, "pubkey": str, "key_id": str}
    """
    ts = ts or _iso_ts()
    obj = {"type": object_type, "id": object_id}
    if object_path is not None:
        obj["path"] = object_path
    body = {
        "prev_hash": prev_hash,
        "ts": ts,
        "scope": scope,
        "actor": actor,
        "action": action,
        "object": obj,
        "payload": payload,
    }
    event_id = compute_event_id(body)
    body["event_id"] = event_id
    # Full envelope for writing (event_id at top level per schema)
    envelope = {
        "event_id": event_id,
        "prev_hash": prev_hash,
        "ts": ts,
        "scope": scope,
        "actor": actor,
        "action": action,
        "object": obj,
        "payload": payload,
        "sig": "",
    }
    if secret_key_hex:
        message = canonical_dumps(body_for_hash(envelope))
        envelope["sig"] = sign(message, secret_key_hex)
    return envelope


def verify_envelope(event: Dict[str, Any]) -> bool:
    """Verify event_id matches recomputed hash and signature (if non-empty) is valid."""
    body = body_for_hash(event)
    computed_id = compute_event_id(body)
    if computed_id != event.get("event_id"):
        return False
    sig = event.get("sig") or ""
    if sig and event.get("actor", {}).get("pubkey"):
        message = canonical_dumps(body)
        if not verify(message, sig, event["actor"]["pubkey"]):
            return False
    return True
