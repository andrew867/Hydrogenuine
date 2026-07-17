"""
Hydrogenuine error types.
"""


class HydrogenuineError(Exception):
    """Base exception for Hydrogenuine."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or "HG_ERROR"


def structured_error_result(
    error: Exception,
    code: str = "HG_ERROR",
    context: dict | None = None,
) -> dict:
    """Return a structured error payload for CLI/logging."""
    return {
        "ok": False,
        "error": str(error),
        "code": code,
        "context": context or {},
    }
