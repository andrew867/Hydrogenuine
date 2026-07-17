"""Social artifact storage: handoff notes, availability rationale, belief override rationale."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _social_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "social"


def _date_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def write_handoff_notes(workspace_root: Path, handoff_id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    root = _social_root(workspace_root) / "handoffs" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{handoff_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "artifact_id": handoff_id}


def write_availability_rationale(workspace_root: Path, rec_id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    root = _social_root(workspace_root) / "availability" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{rec_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "artifact_id": rec_id}


def write_belief_override_rationale(workspace_root: Path, override_id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    root = _social_root(workspace_root) / "belief_overrides" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{override_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "artifact_id": override_id}
