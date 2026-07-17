"""
Control Surface Pack 7: Steering replay via pinsets — snapshot directive refs for replay.
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


def _snapshots_root(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "steering" / "pinset_snapshots"


def publish_steering_pinset_snapshot(
    *,
    target_refs: List[Dict[str, Any]],
    directive_refs: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    value_profile_refs: Optional[List[str]] = None,
    contract_refs: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Publish STEERING_PINSET_SNAPSHOT artifact and emit event.
    directive_refs: list of { directive_id, hash } or { directive_id }.
    Returns snapshot_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    snapshot_id = "snap_" + hashlib.sha256(
        f"{ts}:{len(directive_refs)}:{len(target_refs)}".encode()
    ).hexdigest()[:16]
    root = _snapshots_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    doc: Dict[str, Any] = {
        "snapshot_id": snapshot_id,
        "ts": ts,
        "target_refs": target_refs,
        "directive_refs": directive_refs,
    }
    if value_profile_refs:
        doc["value_profile_refs"] = value_profile_refs
    if contract_refs:
        doc["contract_refs"] = contract_refs
    path = root / f"{snapshot_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    payload = {
        "snapshot_id": snapshot_id,
        "ts": ts,
        "target_refs": target_refs,
        "directive_refs": directive_refs,
        "artifact_path": str(path),
    }
    if value_profile_refs:
        payload["value_profile_refs"] = value_profile_refs
    if contract_refs:
        payload["contract_refs"] = contract_refs
    emit(
        "STEERING_PINSET_SNAPSHOT",
        "steering_pinset_snapshot",
        snapshot_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return snapshot_id


def resolve_steering_snapshot(
    workspace_root: Path,
    snapshot_id: str,
) -> Optional[Dict[str, Any]]:
    """Load steering pinset snapshot from artifacts/steering/pinset_snapshots/{snapshot_id}.json."""
    path = _snapshots_root(workspace_root) / f"{snapshot_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
