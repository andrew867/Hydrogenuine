"""Capability broker errors."""

from __future__ import annotations


class BrokerError(Exception):
    """Base broker error."""


class BrokerValidationError(BrokerError):
    """Input validation failure."""

    def __init__(self, message: str, *, verdict: str):
        self.verdict = verdict
        super().__init__(message)


class BrokerAuditError(BrokerError):
    """Audit log integrity failure."""


__all__ = ["BrokerAuditError", "BrokerError", "BrokerValidationError"]
