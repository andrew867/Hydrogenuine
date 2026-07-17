"""
Dead-letter replay (F3): run from DLQ payload in no-side-effects mode.

Loads a DLQ file and returns decisions/inputs for replay without executing external writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

try:
    from hg_core.deadletter import load_deadletter
except ImportError:
    def load_deadletter(path: Path) -> Dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            import json
            return json.load(f)


def replay_deadletter_run(
    dlq_path: Path,
    workspace_root: Optional[Path] = None,
    no_side_effects: bool = True,
) -> Dict[str, Any]:
    """
    Load a DLQ file and return payload suitable for replay.

    When no_side_effects is True (default), returns the loaded payload with
    run_id, inputs, outputs, error, and any decisions field. Caller can
    re-run the workflow with a no-op dispatcher to reproduce same decisions
    without external writes.

    Returns dict with at least: run_id, task_id, inputs, outputs, error,
    and optionally decisions (if present in payload).
    """
    path = Path(dlq_path)
    if not path.is_absolute() and workspace_root is not None:
        path = Path(workspace_root) / path
    data = load_deadletter(path)
    out = {
        "run_id": data.get("run_id"),
        "task_id": data.get("task_id"),
        "inputs": data.get("inputs", {}),
        "outputs": data.get("outputs", {}),
        "error": data.get("error", {}),
        "written_at": data.get("written_at"),
    }
    if "decisions" in data:
        out["decisions"] = data["decisions"]
    if no_side_effects:
        out["no_side_effects"] = True
    return out
