"""
Optional task_id → dag_path registry for DAG-per-task runs.

When a task has a registered DAG path and HG_USE_TASK_DAG is set,
run_task can run the DAG instead of the tiered run_task path (fallback when not configured).
See hg_core/task_graph/docs/dag_per_task_spec.md and dag_wiring_plan.md §6.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DAG_REGISTRY_PATH = "memory/automation/dag_registry.json"


def get_dag_path(task_name: str, workspace_root: Optional[Path] = None) -> Optional[Path]:
    """
    Return the path to the DAG file for this task if registered and file exists; else None.
    Path in registry is relative to workspace root.
    """
    try:
        from hg_lib.config import get_workspace_root
        root = workspace_root or get_workspace_root()
    except Exception:
        return None
    registry_file = root / DAG_REGISTRY_PATH
    if not registry_file.exists():
        return None
    try:
        with open(registry_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load dag_registry %s: %s", registry_file, e)
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get(task_name)
    if not raw or not isinstance(raw, str):
        return None
    path = root / raw.strip()
    if not path.exists():
        logger.debug("DAG path for %s does not exist: %s", task_name, path)
        return None
    return path
