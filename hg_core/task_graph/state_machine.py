"""
Node status state machine and transition rules.

Only allowed transitions are enforced so scheduler and persistence stay consistent.
"""

from __future__ import annotations

from enum import Enum
from typing import Set, Tuple

# Allowed (from_status, to_status) pairs
_ALLOWED: Set[Tuple[str, str]] = {
    ("pending", "ready"),
    ("pending", "skipped"),
    ("pending", "blocked"),
    ("ready", "running"),
    ("ready", "skipped"),
    ("ready", "blocked"),
    ("running", "done"),
    ("running", "failed"),
    ("running", "ready"),  # retry
}


class NodeStatus(str, Enum):
    """Node execution status."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


def can_transition(from_status: str, to_status: str) -> bool:
    """Return True if transitioning from from_status to to_status is allowed."""
    return (from_status, to_status) in _ALLOWED
