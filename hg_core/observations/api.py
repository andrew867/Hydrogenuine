"""
Observation list/detail/filter API over materialized index.
Sensitive: high/medium pii_class redacted unless reveal=True; reveal emits audited event.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from hg_core.ledger import emit
except ImportError:
    emit = None


def _observations_path(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized" / "observations.jsonl"


def _load_observations(workspace_root: Path) -> List[Dict[str, Any]]:
    path = _observations_path(workspace_root)
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def list_observations(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    signal_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    List observations from materialized index with optional filters.
    """
    workspace_root = Path(workspace_root)
    rows = _load_observations(workspace_root)
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    if signal_id is not None:
        rows = [r for r in rows if r.get("signal_id") == signal_id]
    out = rows[offset : offset + limit]
    result = []
    for r in out:
        if r.get("pii_class") in ("high", "medium"):
            r = dict(r)
            r["payload_ref"] = {"redacted": True, "pii_class": r.get("pii_class")}
            r["payload_inline"] = None
        result.append(r)
    return result


def get_observation(
    workspace_root: Path,
    observation_id: str,
    *,
    reveal: bool = False,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get one observation by observation_id. If pii_class is high/medium and reveal=False,
    payload_ref is redacted. If reveal=True, emit SENSITIVE_REVEAL_REQUESTED and return full row.
    """
    workspace_root = Path(workspace_root)
    for r in _load_observations(workspace_root):
        if r.get("observation_id") != observation_id:
            continue
        pii = r.get("pii_class", "none")
        if pii in ("high", "medium") and not reveal:
            out = dict(r)
            out["payload_ref"] = {"redacted": True, "pii_class": pii}
            out["payload_inline"] = None
            return out
        if pii in ("high", "medium") and reveal and emit:
            try:
                emit(
                    "SENSITIVE_REVEAL_REQUESTED",
                    "observation",
                    observation_id,
                    {"observation_id": observation_id, "pii_class": pii},
                    scope=scope or {"type": "global", "id": "default"},
                    actor=actor,
                    workspace_root=workspace_root,
                )
            except Exception:
                pass
        return r
    return None
