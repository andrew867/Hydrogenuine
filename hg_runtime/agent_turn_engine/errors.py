"""Agent turn engine errors."""

from __future__ import annotations


class AgentTurnError(Exception):
    """Base agent turn engine error."""


class AgentTurnValidationError(AgentTurnError):
    """Invalid turn request or configuration."""


class AgentTurnStorageError(AgentTurnError):
    """Turn artifact storage failure."""


class AgentTurnDispatchError(AgentTurnError):
    """Internal dispatch failure."""


class AgentTurnReplayError(AgentTurnError):
    """Replay verification failure."""


__all__ = [
    "AgentTurnDispatchError",
    "AgentTurnError",
    "AgentTurnReplayError",
    "AgentTurnStorageError",
    "AgentTurnValidationError",
]
