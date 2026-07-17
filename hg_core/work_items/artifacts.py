"""Work item artifact storage: update notes, link refs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _work_items_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "work_items"


def write_update_note(workspace_root: Path, work_item_id: str, update_id: str, obj: Dict[str, Any]) -> str:
    root = _work_items_root(workspace_root) / "updates"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{work_item_id}_{update_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
