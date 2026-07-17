"""
Control Surface Pack 9: Swarm lifecycle — state machine and events.
States: Draft, Simulating, Staged, Live, Paused, Quarantined, Retired.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit

VALID_STATES = frozenset({
    "draft", "simulating", "staged", "live", "paused", "quarantined", "retired",
})


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _swarms_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "swarms"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def create_swarm(
    *,
    name: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    template_id: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Create swarm in Draft. Emit SWARM_CREATED. Returns swarm_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    swarm_id = "swarm_" + hashlib.sha256(f"{name}:{ts}".encode()).hexdigest()[:16]
    payload = {
        "swarm_id": swarm_id,
        "name": name,
        "state": "draft",
        "ts": ts,
        "template_id": template_id or "",
    }
    emit(
        "SWARM_CREATED",
        "swarm",
        swarm_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    root = _materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    swarms_path = root / "swarms.jsonl"
    with open(swarms_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "swarm_id": swarm_id,
            "name": name,
            "state": "draft",
            "created_ts": ts,
            "template_id": template_id or "",
        }, ensure_ascii=False) + "\n")
    return swarm_id


def publish_swarm_config(
    *,
    swarm_id: str,
    config: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Publish swarm config artifact. Emit SWARM_CONFIG_PUBLISHED. Returns artifact path."""
    workspace_root = Path(workspace_root or ".")
    root = _swarms_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    ts = _iso_ts()
    path = root / f"{swarm_id}_config.json"
    doc = {"swarm_id": swarm_id, "ts": ts, **config}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "SWARM_CONFIG_PUBLISHED",
        "swarm_config",
        swarm_id,
        {"swarm_id": swarm_id, "artifact_path": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return str(path)


def _get_swarm_current_state(workspace_root: Path, swarm_id: str) -> Optional[Dict[str, Any]]:
    root = _materialized_root(workspace_root)
    for r in _load_jsonl(root / "swarms.jsonl"):
        if r.get("swarm_id") == swarm_id:
            return r
    return None


def get_swarm_state(workspace_root: Path, swarm_id: str) -> Optional[Dict[str, Any]]:
    """Return current swarm state from materialized swarms.jsonl."""
    return _get_swarm_current_state(Path(workspace_root), swarm_id)


def set_swarm_state(
    *,
    swarm_id: str,
    new_state: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    health_passed: Optional[bool] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Change swarm state. Emit SWARM_STATE_CHANGED.
    Cannot enter live without health_passed=True; can enter staged with writes disabled if most checks pass.
    Returns { event_id, allowed, reason }.
    """
    workspace_root = Path(workspace_root or ".")
    new_state = (new_state or "").strip().lower()
    if new_state not in VALID_STATES:
        return {"event_id": "", "allowed": False, "reason": "invalid_state"}

    current = _get_swarm_current_state(workspace_root, swarm_id)
    if not current:
        return {"event_id": "", "allowed": False, "reason": "swarm_not_found"}

    if new_state == "live" and (health_passed is not True):
        return {"event_id": "", "allowed": False, "reason": "health_checks_required_for_live"}

    ts = _iso_ts()
    event_id = emit(
        "SWARM_STATE_CHANGED",
        "swarm",
        swarm_id,
        {
            "swarm_id": swarm_id,
            "from_state": current.get("state", "draft"),
            "to_state": new_state,
            "ts": ts,
            "health_passed": health_passed,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    # Update materialized state (append-only ledger is source of truth; we update derived view)
    root = _materialized_root(workspace_root)
    rows = _load_jsonl(root / "swarms.jsonl")
    for r in rows:
        if r.get("swarm_id") == swarm_id:
            r["state"] = new_state
            r["updated_ts"] = ts
            break
    with open(root / "swarms.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"event_id": event_id, "allowed": True, "reason": ""}


def list_swarms(
    workspace_root: Path,
    state: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List swarms and states from materialized swarms.jsonl."""
    root = _materialized_root(Path(workspace_root))
    rows = _load_jsonl(root / "swarms.jsonl")
    if state:
        rows = [r for r in rows if (r.get("state") or "").lower() == state.lower()]
    rows.sort(key=lambda r: r.get("updated_ts", r.get("created_ts", "")), reverse=True)
    return rows[:limit]
