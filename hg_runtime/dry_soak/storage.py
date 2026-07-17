"""Dry soak storage paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def dry_soak_root(*, base: Path | None = None) -> Path:
    env = os.environ.get("HG_DRY_SOAK_ROOT")
    if env:
        return Path(env)
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "dry_soak"
    return root


def run_dry_soak_dir(run_id: str, *, base: Path | None = None) -> Path:
    return dry_soak_root(base=base) / run_id


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


__all__ = ["dry_soak_root", "run_dry_soak_dir", "write_json"]
