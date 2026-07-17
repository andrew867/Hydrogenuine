"""Governed work loop errors."""

from __future__ import annotations


class GovernedWorkLoopError(Exception):
    """Base governed work loop error."""


class GovernedEnvelopeError(GovernedWorkLoopError):
    """Envelope validation failure."""


class GovernedWorkRefusedError(GovernedWorkLoopError):
    """Work item refused by envelope/policy."""
