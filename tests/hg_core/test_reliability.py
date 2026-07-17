"""
Pack3 Phase 4: Reliability primitives — circuit breaker, backpressure, retry, timeouts.
"""

import pytest
from hg_core.runtime.reliability import (
    get_llm_timeout_s,
    get_tool_timeout_s,
    get_breaker,
    can_execute_breaker,
    record_breaker_success,
    record_breaker_failure,
    get_all_breaker_states,
    retry_with_jitter,
    concurrency_limiter_acquire,
    concurrency_limiter_release,
)


def test_breaker_opens_after_n_failures():
    """Breaker opens after failure_threshold failures."""
    key = "test_breaker_opens_xyz"
    # Reset any prior state by success
    record_breaker_success(key)
    assert can_execute_breaker(key, failure_threshold=3, recovery_timeout_s=0.1)
    record_breaker_failure(key, failure_threshold=3, recovery_timeout_s=0.1)
    record_breaker_failure(key, failure_threshold=3, recovery_timeout_s=0.1)
    assert can_execute_breaker(key, failure_threshold=3, recovery_timeout_s=0.1)
    record_breaker_failure(key, failure_threshold=3, recovery_timeout_s=0.1)
    assert not can_execute_breaker(key, failure_threshold=3, recovery_timeout_s=0.1)
    record_breaker_success(key)


def test_breaker_resets_after_cooldown():
    """After recovery_timeout_s, breaker goes half_open and allows one call."""
    key = "test_breaker_cooldown_xyz"
    record_breaker_success(key)
    for _ in range(5):
        record_breaker_failure(key, failure_threshold=5, recovery_timeout_s=0.05)
    assert not can_execute_breaker(key, failure_threshold=5, recovery_timeout_s=0.05)
    import time
    time.sleep(0.06)
    assert can_execute_breaker(key, failure_threshold=5, recovery_timeout_s=0.05)
    record_breaker_success(key)


def test_breaker_success_closes():
    """Record success closes breaker and resets count."""
    key = "test_breaker_success_xyz"
    record_breaker_success(key)
    record_breaker_failure(key, failure_threshold=2, recovery_timeout_s=10)
    record_breaker_failure(key, failure_threshold=2, recovery_timeout_s=10)
    assert not can_execute_breaker(key, failure_threshold=2, recovery_timeout_s=10)
    record_breaker_success(key)
    assert can_execute_breaker(key, failure_threshold=2, recovery_timeout_s=10)


def test_get_all_breaker_states():
    """get_all_breaker_states returns list with key, state, failure_count."""
    key = "test_states_xyz"
    record_breaker_success(key)
    record_breaker_failure(key, failure_threshold=10, recovery_timeout_s=60)
    states = get_all_breaker_states()
    found = [s for s in states if s.get("key") == key]
    assert len(found) == 1
    assert found[0]["state"] == "closed"  # only 1 failure, threshold 10
    assert found[0]["failure_count"] == 1
    record_breaker_success(key)


def test_retry_with_jitter_succeeds_first_try():
    """retry_with_jitter returns result on first success."""
    calls = [0]
    def fn():
        calls[0] += 1
        return 42
    assert retry_with_jitter(fn, max_retries=2) == 42
    assert calls[0] == 1


def test_retry_with_jitter_retries_then_succeeds():
    """retry_with_jitter retries on failure then returns."""
    calls = [0]
    def fn():
        calls[0] += 1
        if calls[0] < 2:
            raise ValueError("transient")
        return 43
    assert retry_with_jitter(fn, max_retries=3, base_delay_s=0.01, max_delay_s=0.02) == 43
    assert calls[0] == 2


def test_retry_with_jitter_raises_after_exhausted():
    """retry_with_jitter raises last exception when all retries fail."""
    def fn():
        raise RuntimeError("nope")
    with pytest.raises(RuntimeError, match="nope"):
        retry_with_jitter(fn, max_retries=2, base_delay_s=0.01)


def test_concurrency_limiter_acquire_release():
    """Acquire up to limit succeeds; then fails until release."""
    tenant = "test_tenant_limiter_xyz"
    # Release any leftover from other tests
    for _ in range(10):
        concurrency_limiter_release(tenant)
    # Default limit is 5
    acquired = 0
    while concurrency_limiter_acquire(tenant):
        acquired += 1
        if acquired > 10:
            break
    assert acquired >= 1
    assert not concurrency_limiter_acquire(tenant)
    concurrency_limiter_release(tenant)
    assert concurrency_limiter_acquire(tenant)
    # Cleanup
    for _ in range(acquired + 1):
        concurrency_limiter_release(tenant)


def test_timeouts_positive():
    """Config returns positive timeouts."""
    assert get_llm_timeout_s() >= 10
    assert get_tool_timeout_s() >= 5
