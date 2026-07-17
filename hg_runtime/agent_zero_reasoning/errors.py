"""Reasoning engine errors."""

from __future__ import annotations

from hg_runtime.model_provider_fabric.provider_receipts import ProviderReceipt


class ReasoningEngineError(Exception):
    """Base reasoning engine error."""


class ReasoningParseError(ReasoningEngineError):
    """Model output could not be parsed."""

    def __init__(self, message: str, *, kind: str = "invalid_json"):
        self.kind = kind
        super().__init__(message)


class ReasoningValidationError(ReasoningEngineError):
    """Parsed output failed intent validation."""

    def __init__(self, message: str, *, verdict: str):
        self.verdict = verdict
        super().__init__(message)


class ReasoningProviderError(ReasoningEngineError):
    """Provider boundary failure."""

    def __init__(self, message: str, *, receipt: ProviderReceipt | None = None):
        self.receipt = receipt
        super().__init__(message)


__all__ = [
    "ReasoningEngineError",
    "ReasoningParseError",
    "ReasoningProviderError",
    "ReasoningValidationError",
]
