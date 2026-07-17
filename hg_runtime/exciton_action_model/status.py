"""Action status lifecycle for EXCITON UX Phase 3."""

from __future__ import annotations

from enum import Enum


class AgentActionStatus(str, Enum):
    QUEUED = "queued"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    EXECUTED = "executed"
    FAILED = "failed"
    INVALID = "invalid"
    BLOCKED = "blocked"
    DRY_RUN_ONLY = "dry_run_only"


TERMINAL_STATUSES: frozenset[AgentActionStatus] = frozenset(
    {
        AgentActionStatus.DENIED,
        AgentActionStatus.EXPIRED,
        AgentActionStatus.CANCELLED,
        AgentActionStatus.EXECUTED,
        AgentActionStatus.FAILED,
        AgentActionStatus.INVALID,
        AgentActionStatus.BLOCKED,
    }
)

NON_EXECUTABLE_STATUSES: frozenset[AgentActionStatus] = frozenset(
    TERMINAL_STATUSES | {AgentActionStatus.QUEUED, AgentActionStatus.DRY_RUN_ONLY}
)


def is_executable_status(status: AgentActionStatus) -> bool:
    """Only approved items may execute — and only via a separate executor (out of scope)."""
    return status == AgentActionStatus.APPROVED


__all__ = [
    "AgentActionStatus",
    "NON_EXECUTABLE_STATUSES",
    "TERMINAL_STATUSES",
    "is_executable_status",
]
