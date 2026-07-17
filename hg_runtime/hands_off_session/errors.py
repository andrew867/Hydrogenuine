"""Hands-off session errors."""

from __future__ import annotations


class HandsOffSessionError(Exception):
    """Base hands-off session error."""


class HandsOffConfigError(HandsOffSessionError):
    """Invalid session configuration."""


class HandsOffLockError(HandsOffSessionError):
    """Session lock failure."""


class HandsOffBudgetError(HandsOffSessionError):
    """Watchdog budget exceeded."""
