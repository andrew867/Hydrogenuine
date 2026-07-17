"""
Dead letter queue: failed runs serialized for replay (plan f2).

Path: memory/automation/deadletter/<task_id>/<timestamp>.json
Content: minimal repro (inputs, outputs, error, run_id, hashes) so runs can be replayed.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEADLETTER_ROOT = "memory/automation/deadletter"


def _timestamp_safe() -> str:
    """ISO-like timestamp safe for filenames (colons -> -)."""
    return datetime.now(timezone.utc).isoformat().replace(":", "-").replace("+00:00", "Z")[:26]


def deadletter_path(workspace_root: Path, task_id: str, timestamp: Optional[str] = None) -> Path:
    """Path to a single deadletter file."""
    ts = timestamp or _timestamp_safe()
    return workspace_root / DEADLETTER_ROOT / task_id / f"{ts}.json"


def write_failed_run(
    workspace_root: Path,
    task_id: str,
    run_id: str,
    error: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    output_hashes: Optional[Dict[str, str]] = None,
    timestamp: Optional[str] = None,
) -> Path:
    """
    Write a failed run to the dead letter queue. Returns the path written.
    """
    path = deadletter_path(workspace_root, task_id, timestamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "run_id": run_id,
        "error": error,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "output_hashes": output_hashes or {},
        "written_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError as e:
        logger.warning("Could not write deadletter %s: %s", path, e)
    return path


def list_deadletter_files(workspace_root: Path, task_id: Optional[str] = None) -> list[Path]:
    """List deadletter JSON files, optionally filtered by task_id."""
    root = workspace_root / DEADLETTER_ROOT
    if not root.exists():
        return []
    out = []
    for path in root.iterdir():
        if path.is_dir():
            if task_id is None or path.name == task_id:
                out.extend(path.glob("*.json"))
        elif path.suffix == ".json" and (task_id is None or path.parent.name == task_id):
            out.append(path)
    return sorted(out, key=lambda p: p.name, reverse=True)


def load_deadletter(path: Path) -> Dict[str, Any]:
    """Load a single deadletter JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)
