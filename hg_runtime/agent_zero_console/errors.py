"""Agent Zero Console errors."""

from __future__ import annotations


class ConsoleError(Exception):
    """Base console error."""


class AuthorityInvariantError(ConsoleError):
    """Raised when authority_created or permission_granted would be true."""


class ForbiddenChatActionError(ConsoleError):
    """Chat attempted a forbidden side effect."""


class SentienceClaimError(ConsoleError):
    """Status synthesis attempted sentience/personhood language."""


class OperatorPressureError(ConsoleError):
    """Status synthesis attempted operator-pressure language."""
