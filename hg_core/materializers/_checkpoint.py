"""Checkpoint read/write for materializers (last event_id per scope)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional


def get_materialized_root(workspace_root: Path) -> Path:
    return workspace_root / "memory" / "materialized"


def get_checkpoint_path(workspace_root: Path, name: str) -> Path:
    return get_materialized_root(workspace_root) / "checkpoints" / f"{name}.json"


def load_checkpoint(workspace_root: Path, name: str) -> Dict[str, str]:
    path = get_checkpoint_path(workspace_root, name)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_checkpoint(workspace_root: Path, name: str, checkpoint: Dict[str, str]) -> None:
    path = get_checkpoint_path(workspace_root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=0)
