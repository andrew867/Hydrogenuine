"""
Control Surface Pack 12: Stream message priority (P0/P1/P2) and backpressure.
P0 = safety-critical (never drop), P1 = operational, P2 = telemetry (sample/compress).
Maps to stream_hardening BACKPRESSURE_* for server behavior.
"""
from __future__ import annotations

from .stream_hardening import (
    BACKPRESSURE_PRIORITY_HIGH,
    BACKPRESSURE_PRIORITY_LOW,
    BACKPRESSURE_PRIORITY_NORMAL,
    BACKPRESSURE_PRIORITY_SAFETY_CRITICAL,
    should_drop_for_backpressure,
)

# Pack 12 spec: P0 safety-critical, P1 operational, P2 telemetry
STREAM_PRIORITY_P0 = "P0"
STREAM_PRIORITY_P1 = "P1"
STREAM_PRIORITY_P2 = "P2"

# Map P0/P1/P2 to backpressure priority (never drop P0 = safety_critical)
P_TO_BACKPRESSURE = {
    STREAM_PRIORITY_P0: BACKPRESSURE_PRIORITY_SAFETY_CRITICAL,
    STREAM_PRIORITY_P1: BACKPRESSURE_PRIORITY_HIGH,
    STREAM_PRIORITY_P2: BACKPRESSURE_PRIORITY_NORMAL,
}


def action_to_stream_priority(action: str) -> str:
    """
    Classify ledger/stream action as P0, P1, or P2.
    P0: blocks, safeguards, global controls, incident candidates.
    P1: work item state, approvals, disputes.
    P2: activity feed, chat updates, telemetry.
    """
    p0_actions = {
        "WORK_ITEM_BLOCKED",
        "DRIFT_SAFEGUARD_APPLIED",
        "GLOBAL_CONTROL_APPLIED",
        "GLOBAL_CONTROL_DENIED",
        "INCIDENT_OPENED",
        "ENTITY_PAUSED",
        "ENTITY_RESUMED",
        "CONTROL_OVERRIDE_APPLIED",
    }
    p1_actions = {
        "WORK_ITEM_CREATED",
        "WORK_ITEM_UPDATED",
        "WORK_ITEM_ROUTED",
        "ORCHESTRATION_ACTION_APPLIED",
        "STEERING_DIRECTIVE_APPLIED",
        "AUTONOMY_PRESET_APPLIED",
    }
    if action in p0_actions:
        return STREAM_PRIORITY_P0
    if action in p1_actions:
        return STREAM_PRIORITY_P1
    return STREAM_PRIORITY_P2


def should_drop_event_for_backpressure(priority: str, drop_below: str) -> bool:
    """Return True if event at given priority should be dropped when drop_below is active. Never drops P0."""
    bp = P_TO_BACKPRESSURE.get(priority, BACKPRESSURE_PRIORITY_NORMAL)
    drop_bp = P_TO_BACKPRESSURE.get(drop_below, BACKPRESSURE_PRIORITY_LOW)
    return should_drop_for_backpressure(bp, drop_bp)


def per_connection_budget_default() -> int:
    """Max messages per connection per window before disconnecting abusive clients (default)."""
    return 10_000
