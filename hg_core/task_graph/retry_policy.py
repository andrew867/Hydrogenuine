"""
Retry policy by failure class (F2) for autonomy Phase 1.

Maps each F1 failure class to max_attempts, retryable, backoff_ms, and escalation.
Executor or run_task can use this to decide whether to retry and with what delay.
"""

from __future__ import annotations

from typing import Any, Dict

from .failure_classification import FAILURE_CLASSES

# Default policy per class: max_attempts (total incl first), retryable, retry_backoff_ms, escalation
DEFAULT_RETRY_POLICY: Dict[str, Dict[str, Any]] = {
    "transient_network": {"max_attempts": 4, "retryable": True, "retry_backoff_ms": 2000, "escalation": "alert"},
    "rate_limited": {"max_attempts": 3, "retryable": True, "retry_backoff_ms": 60000, "escalation": "alert"},
    "dependency_unavailable": {"max_attempts": 2, "retryable": True, "retry_backoff_ms": 5000, "escalation": "halt"},
    "validation_failed": {"max_attempts": 1, "retryable": False, "retry_backoff_ms": 0, "escalation": "halt"},
    "safety_blocked": {"max_attempts": 1, "retryable": False, "retry_backoff_ms": 0, "escalation": "alert"},
    "permission_denied": {"max_attempts": 1, "retryable": False, "retry_backoff_ms": 0, "escalation": "halt"},
    "timeout": {"max_attempts": 2, "retryable": True, "retry_backoff_ms": 5000, "escalation": "alert"},
    "internal_error": {"max_attempts": 2, "retryable": True, "retry_backoff_ms": 1000, "escalation": "alert"},
    "unknown": {"max_attempts": 2, "retryable": True, "retry_backoff_ms": 2000, "escalation": "alert"},
}


def get_retry_policy_for_class(failure_class: str) -> Dict[str, Any]:
    """
    Return retry policy for the given failure class.
    Keys: max_attempts, retryable, retry_backoff_ms, escalation.
    """
    if failure_class not in FAILURE_CLASSES:
        failure_class = "unknown"
    return dict(DEFAULT_RETRY_POLICY.get(failure_class, DEFAULT_RETRY_POLICY["unknown"]))


def is_retryable(failure_class: str) -> bool:
    """Return True if this failure class is retryable (max_attempts > 1 and retryable=True)."""
    policy = get_retry_policy_for_class(failure_class)
    return bool(policy.get("retryable")) and (policy.get("max_attempts", 1) or 0) > 1
