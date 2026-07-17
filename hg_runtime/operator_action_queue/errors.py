"""Operator action queue errors — fail closed."""

from __future__ import annotations


class OperatorQueueError(Exception):
    """Base queue error."""


class QueueCorruptError(OperatorQueueError):
    """Queue file corrupt or unreadable — fail closed."""


class InvalidTransitionError(OperatorQueueError):
    """Illegal status transition."""


class StopPanicActiveError(OperatorQueueError):
    """Stop or panic blocks approval/eligibility."""


class SelfApprovalError(OperatorQueueError):
    """Source agent cannot approve its own item."""


class NotExecutableError(OperatorQueueError):
    """Item not eligible for execution marking."""


class SecretLeakError(OperatorQueueError):
    """Forbidden field detected in queue payload."""


class ItemNotFoundError(OperatorQueueError):
    """Queue item not found."""


__all__ = [
    "InvalidTransitionError",
    "ItemNotFoundError",
    "NotExecutableError",
    "OperatorQueueError",
    "QueueCorruptError",
    "SecretLeakError",
    "SelfApprovalError",
    "StopPanicActiveError",
]
