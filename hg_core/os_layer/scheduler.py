"""
Job queue with priorities: incident/anomaly first, then high/urgent, then normal/low.
Reads from materialized work_items.jsonl.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.materializers._checkpoint import get_materialized_root

PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
TYPE_PRIORITY = {"incident": 0, "anomaly": 1, "investigation": 2, "decision": 3, "change": 4, "task": 5}


def _load_work_items(root: Path) -> List[Dict[str, Any]]:
    path = root / "work_items.jsonl"
    if not path.exists():
        return []
    out = []
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


def get_prioritized_work_items(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    status_filter: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Return work items sorted by priority: type (incident/anomaly first), then priority (urgent first), then created_ts.
    status_filter: e.g. ["proposed", "active"] to exclude done/abandoned.
    """
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    items = _load_work_items(root)
    if scope_type is not None:
        items = [i for i in items if i.get("scope_type") == scope_type]
    if scope_id is not None:
        items = [i for i in items if i.get("scope_id") == scope_id]
    if status_filter is not None:
        items = [i for i in items if i.get("status") in status_filter]
    else:
        items = [i for i in items if i.get("status") not in ("done", "abandoned")]
    def key(i: Dict[str, Any]) -> tuple:
        wi_type = i.get("type", "task")
        pr = i.get("priority", "normal")
        ts = i.get("created_ts") or i.get("updated_ts") or ""
        return (TYPE_PRIORITY.get(wi_type, 5), PRIORITY_ORDER.get(pr, 2), ts)
    items.sort(key=key)
    return items[:limit]
