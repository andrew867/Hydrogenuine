"""Two-phase commit artifacts: proposal, receipt (mandatory for execute)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _side_effects_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "side_effects"


def write_proposal(workspace_root: Path, action_id: str, obj: Dict[str, Any]) -> str:
    root = _side_effects_root(workspace_root) / "proposals"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{action_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def write_receipt(workspace_root: Path, action_id: str, obj: Dict[str, Any]) -> str:
    """Receipt artifact mandatory for ACTION_EXECUTED; records execution outcome."""
    root = _side_effects_root(workspace_root) / "receipts"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{action_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
