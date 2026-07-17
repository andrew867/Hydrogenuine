"""Dry autonomous loop storage paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def loop_root(*, base: Path | None = None) -> Path:
    env = os.environ.get("HG_DRY_AUTONOMOUS_LOOP_ROOT")
    if env:
        return Path(env)
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "dry_autonomous_loop"
    return root


def current_lock_path(*, base: Path | None = None) -> Path:
    return loop_root(base=base) / "current_loop.lock"


def run_loop_dir(run_id: str, *, base: Path | None = None) -> Path:
    return loop_root(base=base) / run_id


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


__all__ = ["current_lock_path", "loop_root", "run_loop_dir", "write_json"]
