"""Live read endurance errors."""

from __future__ import annotations


class LiveReadEnduranceError(Exception):
    """Base live read endurance error."""


class LiveReadWriteScopeDetected(LiveReadEnduranceError):
    """Write scope detected — RED."""


class LiveReadCredentialError(LiveReadEnduranceError):
    """Credential scope or availability error."""
