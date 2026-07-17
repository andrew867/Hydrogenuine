"""
Control Surface Pack 10: Shared impact views — cross-swarm impact graph and blast radius.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


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


def explore_impact(
    workspace_root: Path,
    swarm_ids: Optional[List[str]] = None,
    include_incidents: bool = True,
    include_work_items: bool = True,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Explore cross-swarm impact graph and blast radius.
    Returns { incidents: [], work_items: [], blast_radius: { by_swarm: {}, total_affected } }.
    """
    workspace_root = Path(workspace_root)
    root = _materialized_root(workspace_root)
    incidents: List[Dict[str, Any]] = []
    if include_incidents:
        for r in _load_jsonl(root / "incidents.jsonl")[:limit]:
            if swarm_ids and (r.get("swarm_id") or r.get("scope_id")) not in swarm_ids:
                continue
            incidents.append(r)

    work_items: List[Dict[str, Any]] = []
    if include_work_items:
        for r in _load_jsonl(root / "work_items.jsonl")[:limit]:
            scope = r.get("scope_id") or "default"
            if swarm_ids and scope not in swarm_ids:
                continue
            work_items.append(r)

    by_swarm: Dict[str, int] = {}
    for wi in work_items:
        sid = wi.get("scope_id") or "default"
        by_swarm[sid] = by_swarm.get(sid, 0) + 1
    for inc in incidents:
        sid = inc.get("swarm_id") or inc.get("scope_id") or "default"
        by_swarm[sid] = by_swarm.get(sid, 0) + 0

    return {
        "incidents": incidents,
        "work_items": work_items,
        "blast_radius": {
            "by_swarm": by_swarm,
            "total_affected": len(work_items) + len(incidents),
        },
    }
