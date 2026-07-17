"""Fleet rollups."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.swarms import list_swarms


def _mat(ws: Path) -> Path:
    return Path(ws) / "memory" / "materialized"


def _jl(path: Path) -> List[Dict[str, Any]]:
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


def get_fleet_swarms_with_rollups(workspace_root: Path, state: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    swarms = list_swarms(Path(workspace_root), state=state, limit=limit)
    root = _mat(workspace_root)
    drift = _jl(root / "drift_scores.jsonl")
    wi = _jl(root / "work_items.jsonl")
    inc = _jl(root / "incidents.jsonl")
    open_inc = [x for x in inc if x.get("status") not in ("resolved", "closed")]
    for s in swarms:
        s["rollup"] = {
            "drift_score_count": len(drift),
            "max_drift_score": max((r.get("score") or 0) for r in drift) if drift else 0,
            "incidents_open": len(open_inc),
            "work_items_total": len(wi),
            "work_items_blocked": len([x for x in wi if x.get("status") == "blocked"]),
        }
    return swarms
