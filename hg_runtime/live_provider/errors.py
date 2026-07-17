"""Live provider errors."""

from __future__ import annotations


class LiveProviderError(Exception):
    """Base live provider error."""


class LiveProviderConfigError(LiveProviderError):
    """Invalid live provider configuration."""


class LiveProviderUnavailable(LiveProviderError):
    """Provider honestly unavailable."""

    def __init__(self, message: str, *, verdict: str | None = None, health_receipt=None):
        super().__init__(message)
        self.verdict = verdict
        self.health_receipt = health_receipt


class LiveProviderOutputError(LiveProviderError):
    """Provider output rejected."""

    def __init__(self, message: str, *, output_receipt=None):
        super().__init__(message)
        self.output_receipt = output_receipt


class LiveProviderNonCognitiveDenied(LiveProviderError):
    """Fallback/fixture/mock cannot become cognition."""

    def __init__(self, message: str, *, output_receipt=None):
        super().__init__(message)
        self.output_receipt = output_receipt
