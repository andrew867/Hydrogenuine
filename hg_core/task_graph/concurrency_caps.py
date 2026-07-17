"""
Concurrency caps (Q2): global and per-workflow limits.

In-memory counters for single-process use; extend with file/Redis for multi-process.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

# In-process counters (single runner). For multi-process, use file or Redis.
_global_count: int = 0
_per_workflow: Dict[str, int] = {}
_limits: Dict[str, int] = {"global": 10, "per_workflow": 2}


def set_limits(global_max: Optional[int] = None, per_workflow_max: Optional[int] = None) -> None:
    """Set global and per-workflow concurrency limits."""
    if global_max is not None:
        _limits["global"] = global_max
    if per_workflow_max is not None:
        _limits["per_workflow"] = per_workflow_max


def try_acquire(workflow_id: str) -> bool:
    """
    Try to acquire a concurrency slot for workflow_id.
    Returns True if acquired (global and per-workflow under cap), False otherwise.
    """
    global _global_count, _per_workflow
    if _global_count >= _limits["global"]:
        return False
    if _per_workflow.get(workflow_id, 0) >= _limits["per_workflow"]:
        return False
    _global_count += 1
    _per_workflow[workflow_id] = _per_workflow.get(workflow_id, 0) + 1
    return True


def release(workflow_id: str) -> None:
    """Release a concurrency slot for workflow_id."""
    global _global_count, _per_workflow
    _global_count = max(0, _global_count - 1)
    n = _per_workflow.get(workflow_id, 0)
    if n > 0:
        _per_workflow[workflow_id] = n - 1
