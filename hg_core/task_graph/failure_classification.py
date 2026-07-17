"""
Failure classification (F1) for autonomy Phase 0.

Maps every failure to one of the standard F1 classes so that run traces
and summaries always emit failure_class, message, and minimal context.
"""

from __future__ import annotations

from typing import Any, Dict

FAILURE_CLASSES = (
    "transient_network",
    "rate_limited",
    "dependency_unavailable",
    "validation_failed",
    "safety_blocked",
    "permission_denied",
    "timeout",
    "internal_error",
    "unknown",
)


def classify_failure(exc: BaseException, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Classify an exception into an F1 failure class.

    Returns dict with:
      - failure_class: one of FAILURE_CLASSES
      - message: string (from exception or derived)
      - context: dict (node_id, attempt, etc.; merged with input context)
    """
    ctx = dict(context or {})
    msg = str(exc) or type(exc).__name__
    exc_type = type(exc).__name__

    # Check message/attributes for known signals
    msg_lower = msg.lower()
    if "429" in msg or "rate limit" in msg_lower or "too many requests" in msg_lower:
        return _result("rate_limited", msg, ctx)
    if "safety_blocked" in msg_lower or "content policy" in msg_lower or "safety gate" in msg_lower:
        return _result("safety_blocked", msg, ctx)
    if "timeout" in msg_lower or "timed out" in msg_lower:
        return _result("timeout", msg, ctx)
    if (
        "permission" in msg_lower
        or "scope not allowed" in msg_lower
        or "denied" in msg_lower
        or "do not have access" in msg_lower
    ):
        return _result("permission_denied", msg, ctx)
    if "duplicate content" in msg_lower or "duplicate thread" in msg_lower or "semantic similarity" in msg_lower:
        return _result("validation_failed", msg, ctx)
    if "validation" in msg_lower or "invalid input" in msg_lower or "missing field" in msg_lower:
        return _result("validation_failed", msg, ctx)

    # Type-based classification
    if isinstance(exc, TimeoutError):
        return _result("timeout", msg, ctx)
    if isinstance(exc, PermissionError):
        return _result("permission_denied", msg, ctx)
    if isinstance(exc, FileNotFoundError):
        return _result("dependency_unavailable", msg, ctx)
    if isinstance(exc, ValueError):
        return _result("validation_failed", msg, ctx)
    if isinstance(exc, ConnectionError):
        return _result("transient_network", msg, ctx)
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (110, 111, 113, 114):
        return _result("transient_network", msg, ctx)

    try:
        import urllib.error
        if isinstance(exc, (urllib.error.URLError, urllib.error.HTTPError)):
            if getattr(exc, "code", None) == 429:
                return _result("rate_limited", msg, ctx)
            return _result("transient_network", msg, ctx)
    except ImportError:
        pass

    # Generic RuntimeError / Exception: internal_error vs unknown
    if isinstance(exc, RuntimeError) and "unexpected" in msg_lower:
        return _result("internal_error", msg, ctx)
    if exc_type in ("RuntimeError", "AssertionError", "KeyError", "TypeError", "AttributeError"):
        return _result("internal_error", msg, ctx)

    return _result("unknown", msg, ctx)


def _result(failure_class: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "failure_class": failure_class,
        "message": message,
        "context": context,
    }


def failure_class_from_error_dict(error: Dict[str, Any], node_id: str | None = None) -> str:
    """
    Derive failure_class from an existing node.error dict (e.g. from dispatch return).
    Used when building summary from already-set node.error that may not have failure_class.
    """
    if not isinstance(error, dict):
        return "unknown"
    if "failure_class" in error and error["failure_class"] in FAILURE_CLASSES:
        return error["failure_class"]
    code = (error.get("code") or error.get("type") or "").upper()
    msg = (error.get("message") or "").lower()
    if "STEERING_BLOCKED" in code or "BLOCKED" in code:
        return "safety_blocked"
    if "429" in str(code) or "rate" in msg:
        return "rate_limited"
    if "timeout" in msg or "TIMEOUT" in code:
        return "timeout"
    if "permission" in msg or "PERMISSION" in code or "SCOPE" in code:
        return "permission_denied"
    if "validation" in msg or "VALIDATION" in code or "INPUT_RESOLUTION" in code:
        return "validation_failed"
    if "duplicate content" in msg or "duplicate thread" in msg or "semantic similarity" in msg:
        return "validation_failed"
    if "do not have access" in msg:
        return "permission_denied"
    if "safety" in msg or "SAFETY" in code:
        return "safety_blocked"
    return "unknown"
