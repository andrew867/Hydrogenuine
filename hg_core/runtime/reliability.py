"""
Pack3 Phase 4: Reliability primitives — timeouts, retries, circuit breakers, backpressure.

- Timeouts: configurable LLM and tool call timeouts (env).
- Retries: retry_with_jitter for transient failures.
- Circuit breaker: per key (e.g. tool name, llm:provider); opens after N failures, cooldown, half-open.
- Backpressure: max concurrent tool runs per tenant; overflow yields 429.
"""

from __future__ import annotations

import os
import random
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")

# ---- Config (env) ----
def get_llm_timeout_s() -> int:
    """LLM call timeout in seconds. Env HG_LLM_TIMEOUT_S or default 120."""
    return max(10, int(os.environ.get("HG_LLM_TIMEOUT_S", "120")))


def get_tool_timeout_s() -> int:
    """Tool call timeout in seconds. Env HG_TOOL_TIMEOUT_S or default 60."""
    return max(5, int(os.environ.get("HG_TOOL_TIMEOUT_S", "60")))


# ---- Circuit breaker ----
_BREAKER_STATES = ("closed", "open", "half_open")
_BREAKERS: Dict[str, Dict[str, Any]] = {}
_BREAKER_LOCK = threading.Lock()
_DEFAULT_FAILURE_THRESHOLD = 5
_DEFAULT_RECOVERY_TIMEOUT_S = 60


def _get_breaker_unsafe(key: str, failure_threshold: int, recovery_timeout_s: float) -> Dict[str, Any]:
    """Must be called with _BREAKER_LOCK held."""
    if key not in _BREAKERS:
        _BREAKERS[key] = {
            "state": "closed",
            "failure_count": 0,
            "last_failure_ts": None,
            "failure_threshold": failure_threshold,
            "recovery_timeout_s": recovery_timeout_s,
        }
    return _BREAKERS[key]


def get_breaker(
    key: str,
    *,
    failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout_s: float = _DEFAULT_RECOVERY_TIMEOUT_S,
) -> Dict[str, Any]:
    """Return breaker state dict for key (e.g. tool:gateway.echo or llm:openai)."""
    with _BREAKER_LOCK:
        return dict(_get_breaker_unsafe(key, failure_threshold, recovery_timeout_s))


def can_execute_breaker(
    key: str,
    *,
    failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout_s: float = _DEFAULT_RECOVERY_TIMEOUT_S,
) -> bool:
    """True if execution is allowed (closed or half_open and past cooldown)."""
    with _BREAKER_LOCK:
        b = _get_breaker_unsafe(key, failure_threshold, recovery_timeout_s)
        state = b["state"]
        if state == "closed":
            return True
        if state == "half_open":
            return True
        # open: check recovery timeout
        last = b.get("last_failure_ts")
        if last and (time.monotonic() - last) >= recovery_timeout_s:
            b["state"] = "half_open"
            return True
        return False


def record_breaker_success(key: str) -> None:
    """Record success; reset breaker to closed."""
    with _BREAKER_LOCK:
        b = _get_breaker_unsafe(key, _DEFAULT_FAILURE_THRESHOLD, _DEFAULT_RECOVERY_TIMEOUT_S)
        b["state"] = "closed"
        b["failure_count"] = 0


def record_breaker_failure(
    key: str,
    *,
    failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout_s: float = _DEFAULT_RECOVERY_TIMEOUT_S,
) -> None:
    """Record failure; may open breaker."""
    with _BREAKER_LOCK:
        b = _get_breaker_unsafe(key, failure_threshold, recovery_timeout_s)
        b["failure_count"] = b.get("failure_count", 0) + 1
        b["last_failure_ts"] = time.monotonic()
        if b["failure_count"] >= failure_threshold:
            b["state"] = "open"


def reset_breakers_for_tests() -> None:
    """Clear all circuit-breaker state. Test-isolation helper only.

    The breaker registry ``_BREAKERS`` is a module-level global keyed by breaker
    name; threshold/recovery/state are captured at first creation and persist for
    the process. Under xdist (loadscope) a prior same-worker test that touched
    ``tool:gateway.echo`` leaves stale state, making a later
    ``record_breaker_failure(..., failure_threshold=1)`` / invoke outcome order
    dependent (nondeterministic 200-vs-503). Resetting at each test boundary
    restores isolation. Not used in production paths.
    """
    with _BREAKER_LOCK:
        _BREAKERS.clear()


def get_all_breaker_states() -> List[Dict[str, Any]]:
    """Return list of breaker state dicts for operator visibility."""
    with _BREAKER_LOCK:
        out = []
        for key, b in list(_BREAKERS.items()):
            out.append({
                "key": key,
                "state": b["state"],
                "failure_count": b["failure_count"],
                "last_failure_ts": b.get("last_failure_ts"),
                "failure_threshold": b.get("failure_threshold", _DEFAULT_FAILURE_THRESHOLD),
                "recovery_timeout_s": b.get("recovery_timeout_s", _DEFAULT_RECOVERY_TIMEOUT_S),
            })
        return out


# ---- Retries with jitter ----
def retry_with_jitter(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay_s: float = 1.0,
    max_delay_s: float = 10.0,
    jitter: bool = True,
    is_retryable: Optional[Callable[[Exception], bool]] = None,
) -> T:
    """
    Call fn(); on failure retry up to max_retries with exponential backoff and jitter.
    Raises last exception if all retries fail. is_retryable(e) can filter which errors to retry.
    """
    last: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            if is_retryable and not is_retryable(e):
                raise
            if attempt == max_retries:
                raise
            delay = min(base_delay_s * (2 ** attempt), max_delay_s)
            if jitter:
                delay = delay * (0.5 + random.random())
            time.sleep(delay)
    if last:
        raise last
    raise RuntimeError("retry_with_jitter: unexpected")


# ---- Backpressure: concurrent tool runs per tenant ----
_TOOL_SLOTS: Dict[str, int] = {}
_TOOL_SLOTS_LOCK = threading.Lock()
_DEFAULT_MAX_CONCURRENT_TOOL_RUNS = 5


def _max_concurrent_tool_runs() -> int:
    return max(1, int(os.environ.get("HG_MAX_CONCURRENT_TOOL_RUNS_PER_TENANT", str(_DEFAULT_MAX_CONCURRENT_TOOL_RUNS))))


def concurrency_limiter_acquire(tenant_id: str) -> bool:
    """
    Try to acquire a slot for a tool run in this tenant. Returns True if acquired, False if at limit (caller should 429).
    """
    max_slots = _max_concurrent_tool_runs()
    with _TOOL_SLOTS_LOCK:
        current = _TOOL_SLOTS.get(tenant_id, 0)
        if current >= max_slots:
            return False
        _TOOL_SLOTS[tenant_id] = current + 1
        return True


def concurrency_limiter_release(tenant_id: str) -> None:
    """Release a slot after tool run completes."""
    with _TOOL_SLOTS_LOCK:
        current = _TOOL_SLOTS.get(tenant_id, 0)
        if current > 0:
            _TOOL_SLOTS[tenant_id] = current - 1


@contextmanager
def concurrency_limiter(tenant_id: str):
    """Context manager: acquire on enter, release on exit. Raises if at limit (caller can catch and return 429)."""
    if not concurrency_limiter_acquire(tenant_id):
        raise RuntimeError("concurrency_limit_exceeded")
    try:
        yield
    finally:
        concurrency_limiter_release(tenant_id)
