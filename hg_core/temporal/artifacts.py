"""
Temporal artifact storage: episode summaries, causal mechanism, branch notes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _temporal_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "temporal"


def _date_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def write_episode_summary(workspace_root: Path, episode_id: str, summary: Dict[str, Any]) -> Dict[str, Any]:
    """Write episode summary JSON; return {path, artifact_id}."""
    root = _temporal_root(workspace_root) / "episodes" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{episode_id}_summary.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "artifact_id": f"ep_summary_{episode_id}"}


def write_causal_mechanism(workspace_root: Path, link_id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    """Write causal mechanism JSON; return {path, artifact_id}."""
    root = _temporal_root(workspace_root) / "causality" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{link_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "artifact_id": link_id}


def write_branch_notes(workspace_root: Path, branch_id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    """Write branch notes JSON; return {path, artifact_id}."""
    root = _temporal_root(workspace_root) / "branches" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{branch_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "artifact_id": branch_id}
