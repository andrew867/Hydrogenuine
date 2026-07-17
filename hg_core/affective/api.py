"""
API: current regulatory state, applied modulations, overrides (with expiry).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state import get_regulatory_state_snapshot
from .policy import load_regulatory_policy


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
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


def get_current_regulatory_state(
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Current regulatory state snapshot (evidence-derived)."""
    return get_regulatory_state_snapshot(workspace_root, scope_type, scope_id, agent_id=agent_id, at_ts=None)


def list_applied_modulations(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List MODULATION_APPLIED events from materialized view."""
    root = _materialized_root(Path(workspace_root))
    path = root / "applied_modulations.jsonl"
    rows = _load_jsonl(path)
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    if agent_id is not None:
        rows = [r for r in rows if r.get("agent_id") == agent_id]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]


def list_regulatory_overrides(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    active_only: bool = True,
    at_ts: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List regulatory overrides. If active_only, exclude revoked and expired (expiry_ts < at_ts or now)."""
    root = _materialized_root(Path(workspace_root))
    path = root / "regulatory_overrides.jsonl"
    rows = _load_jsonl(path)
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    if active_only:
        rows = [r for r in rows if not r.get("revoked", False)]
        ref_ts = at_ts
        if not ref_ts:
            from datetime import datetime, timezone
            ref_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        rows = [r for r in rows if (r.get("expiry_ts") or "") > ref_ts]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]


def get_regulatory_policy(workspace_root: Path) -> Dict[str, Any]:
    """Load current regulatory policy artifact."""
    return load_regulatory_policy(Path(workspace_root))
