"""
Control Surface Pack 4: Stream hardening contract — heartbeat, reconnect, backpressure, degrade to polling.
SSE/WS server implementations use these constants and helpers; UI degrades to polling when suggest_polling() True.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Heartbeat interval for SSE/WS (seconds)
HEARTBEAT_INTERVAL_SECONDS = 15

# Backpressure: drop updates below this priority when under load (server-side)
BACKPRESSURE_PRIORITY_SAFETY_CRITICAL = "safety_critical"
BACKPRESSURE_PRIORITY_HIGH = "high"
BACKPRESSURE_PRIORITY_NORMAL = "normal"
BACKPRESSURE_PRIORITY_LOW = "low"

# After this many consecutive stream failures, suggest switching to polling
STREAM_FAILURES_BEFORE_POLLING = 3


def suggest_polling(stream_failures_count: int) -> bool:
    """Return True if client should switch to polling (e.g. after repeated reconnect failures)."""
    return stream_failures_count >= STREAM_FAILURES_BEFORE_POLLING


def should_drop_for_backpressure(priority: str, drop_below_priority: str) -> bool:
    """Return True if this update should be dropped when applying backpressure."""
    order = (BACKPRESSURE_PRIORITY_LOW, BACKPRESSURE_PRIORITY_NORMAL, BACKPRESSURE_PRIORITY_HIGH, BACKPRESSURE_PRIORITY_SAFETY_CRITICAL)
    try:
        return order.index(priority) < order.index(drop_below_priority)
    except ValueError:
        return True


def resume_from(last_event_id: Optional[str], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter events to those after last_event_id (for client reconnect).
    events should be ordered by event_id or ts; returns events after the one matching last_event_id.
    """
    if not last_event_id or not events:
        return list(events)
    for i, ev in enumerate(events):
        if ev.get("event_id") == last_event_id:
            return events[i + 1:]
    return list(events)
