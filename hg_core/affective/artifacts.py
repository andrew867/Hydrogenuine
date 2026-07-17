"""Affective/regulatory artifact storage: modulation rationale, override rationale."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _affective_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "affective"


def _date_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def write_modulation_rationale(workspace_root: Path, modulation_id: str, obj: Dict[str, Any]) -> str:
    root = _affective_root(workspace_root) / "modulation" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{modulation_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def write_override_rationale(workspace_root: Path, override_id: str, obj: Dict[str, Any]) -> str:
    root = _affective_root(workspace_root) / "override" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{override_id}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
