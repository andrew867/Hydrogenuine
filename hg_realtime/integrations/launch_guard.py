"""Launch guards: prevent duplicate concurrent runs for shared workflows."""

from __future__ import annotations

from typing import Any, Optional

_SOCIAL_WORKFLOW_IDS = frozenset({"social-media", "social_media_v1"})
_ACTIVE_STATUSES = (
    "running",
    "launching",
    "approved_pending_launch",
    "pending_approval",
    "pending",
)


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return {}


def social_workflow_in_flight(*, task_name: Optional[str] = None) -> bool:
    """Return True when a social-media workflow run is already active."""
    try:
        from hg_gateway.db import get_connection
    except Exception:
        return False
    placeholders = ",".join("?" for _ in _ACTIVE_STATUSES)
    graph_placeholders = ",".join("?" for _ in _SOCIAL_WORKFLOW_IDS)
    params: list[Any] = list(_SOCIAL_WORKFLOW_IDS) + list(_ACTIVE_STATUSES)
    query = f"""
        SELECT run_id, graph_id, status
        FROM runs
        WHERE graph_id IN ({graph_placeholders})
          AND status IN ({placeholders})
        LIMIT 1
    """
    try:
        with get_connection() as c:
            row = c.execute(query, params).fetchone()
    except Exception:
        return False
    if not row:
        return False
    if not task_name:
        return True
    # Optional: same task_name coalescing could be added via run_dir/summary scan later.
    return True


def should_skip_launch(workflow_id: str, resolved_inputs: Optional[dict[str, Any]] = None) -> tuple[bool, str]:
    """Return (skip, reason) when a launch should be deferred."""
    wf = str(workflow_id or "").strip()
    if wf not in _SOCIAL_WORKFLOW_IDS:
        return False, ""
    if social_workflow_in_flight():
        return True, "social-media workflow already in flight"
    return False, ""
