"""Swarm tree: parent/child run_ids for dashboard. Phase 9."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _workspace_root() -> Optional[Path]:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def get_swarm_tree(run_id: str) -> Dict[str, Any]:
    """
    Return { child_run_ids: [...], parent_run_id?: str } for run_id.
    Reads from memory/automation/swarm_runs/{run_id}.json for child_run_ids.
    Parent is found by scanning swarm_runs for a file that lists this run_id in child_run_ids.
    """
    root = _workspace_root()
    out: Dict[str, Any] = {"run_id": run_id, "child_run_ids": [], "parent_run_id": None}
    if not root:
        return out
    swarm_dir = root / "memory" / "automation" / "swarm_runs"
    if not swarm_dir.is_dir():
        return out

    # This run as swarm parent: read swarm_runs/{run_id}.json
    artifact_path = swarm_dir / f"{run_id}.json"
    if artifact_path.exists():
        try:
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
            out["child_run_ids"] = list(data.get("child_run_ids") or [])
        except (json.JSONDecodeError, OSError):
            pass

    # This run as child: find parent by scanning
    for path in swarm_dir.glob("*.json"):
        if path.stem == run_id:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            children = data.get("child_run_ids") or []
            if run_id in children:
                out["parent_run_id"] = path.stem
                break
        except (json.JSONDecodeError, OSError):
            continue
    return out
