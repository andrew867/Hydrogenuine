"""Extended dry autonomy storage paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def extended_root(*, base: Path | None = None) -> Path:
    env = os.environ.get("HG_EXTENDED_DRY_AUTONOMY_ROOT")
    if env:
        return Path(env)
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "extended_dry_autonomy"
    return root


def current_lock_path(*, base: Path | None = None) -> Path:
    return extended_root(base=base) / "current_loop.lock"


def run_dir(run_id: str, *, base: Path | None = None) -> Path:
    return extended_root(base=base) / run_id


def checkpoint_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "checkpoints"


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


__all__ = ["checkpoint_dir", "current_lock_path", "extended_root", "run_dir", "write_json"]
