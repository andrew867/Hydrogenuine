"""
Interop Pack 2: Memory capsules - portable, signed, redaction-aware bundles.
MEMORY_CAPSULE_PUBLISHED, MEMORY_CAPSULE_SHARED, MEMORY_CAPSULE_IMPORTED, MEMORY_CAPSULE_REJECTED.
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


def publish_memory_capsule(
    *,
    scope: Dict[str, str],
    expires_ts: str,
    redaction_level: str,
    manifests: Dict[str, Any],
    scope_ledger: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    included_events: Optional[List[Dict[str, Any]]] = None,
    included_artifacts: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build capsule artifact (signed), emit MEMORY_CAPSULE_PUBLISHED. Returns capsule_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    capsule_id = "capsule_" + hashlib.sha256(f"{ts}:{redaction_level}".encode()).hexdigest()[:16]
    body = {
        "scope": scope,
        "created_ts": ts,
        "expires_ts": expires_ts,
        "manifests": manifests,
        "redaction_level": redaction_level,
        "included_events": included_events or [],
        "included_artifacts": included_artifacts or [],
    }
    integrity = {"hash": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:32]}
    body["integrity"] = integrity
    root = workspace_root / "artifacts" / "memory_capsules"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{capsule_id}.json"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    emit(
        "MEMORY_CAPSULE_PUBLISHED",
        "memory_capsule",
        capsule_id,
        {"capsule_id": capsule_id, "artifact_id": str(path), "redaction_level": redaction_level, "ts": ts},
        scope=scope_ledger,
        actor=actor,
        workspace_root=workspace_root,
    )
    return capsule_id


def share_capsule(
    *,
    capsule_id: str,
    recipient_ref: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit MEMORY_CAPSULE_SHARED (A2A attachment). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "MEMORY_CAPSULE_SHARED",
        "memory_capsule",
        capsule_id,
        {"capsule_id": capsule_id, "recipient_ref": recipient_ref, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def import_capsule(
    *,
    capsule_id: str,
    capsule: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    max_redaction_level: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Validate and record import. Returns (accepted, event_id). Rejects on expiry or classification mismatch."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    exp = capsule.get("expires_ts")
    if not exp or exp <= ts:
        ev = emit(
            "MEMORY_CAPSULE_REJECTED",
            "memory_capsule",
            capsule_id,
            {"capsule_id": capsule_id, "reason": "expired", "ts": ts},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev
    redaction = capsule.get("redaction_level", "")
    _order = {"low": 0, "medium": 1, "high": 2}
    r_val = _order.get(redaction, 0)
    max_val = _order.get(max_redaction_level or "", 999)
    if max_redaction_level and redaction and r_val > max_val:
        ev = emit(
            "MEMORY_CAPSULE_REJECTED",
            "memory_capsule",
            capsule_id,
            {"capsule_id": capsule_id, "reason": "classification_mismatch", "ts": ts},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev
    ev = emit(
        "MEMORY_CAPSULE_IMPORTED",
        "memory_capsule",
        capsule_id,
        {"capsule_id": capsule_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, ev


def load_capsule(workspace_root: Path, capsule_id: str) -> Optional[Dict[str, Any]]:
    """Load capsule from artifacts/memory_capsules/{capsule_id}.json."""
    path = workspace_root / "artifacts" / "memory_capsules" / f"{capsule_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def verify_capsule_signature(capsule: Dict[str, Any]) -> bool:
    """Verify capsule integrity hash. Returns True if integrity matches."""
    if not capsule or not capsule.get("integrity"):
        return False
    integrity = capsule.get("integrity")
    body_copy = {k: v for k, v in capsule.items() if k != "integrity"}
    expected = hashlib.sha256(json.dumps(body_copy, sort_keys=True).encode()).hexdigest()[:32]
    return integrity.get("hash") == expected if isinstance(integrity, dict) else False
