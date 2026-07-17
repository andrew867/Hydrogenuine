"""Tests for autonomy Phase 1: dedupe/ledger (C2), retry by class (F2), DLQ (F3), circuit breakers (F5)."""

import json
import pytest
from pathlib import Path

from hg_core.posting_dedupe import (
    make_dedupe_key,
    get_date_bucket,
    check_already_posted,
    record_posted,
)

try:
    from hg_core.task_graph.retry_policy import (
        get_retry_policy_for_class,
        is_retryable,
    )
except ImportError:
    get_retry_policy_for_class = None
    is_retryable = None

try:
    from hg_core.deadletter import write_failed_run, load_deadletter, list_deadletter_files
    from hg_core.task_graph.deadletter_replay import replay_deadletter_run
except ImportError:
    replay_deadletter_run = None

try:
    from hg_core.task_graph.circuit_breaker import (
        CircuitBreaker,
        record_failure,
        allow_side_effect,
        reset_breaker,
    )
except ImportError:
    CircuitBreaker = None
    record_failure = None
    allow_side_effect = None
    reset_breaker = None


# --- C2: Dedupe key and ledger ---


def test_dedupe_key_generation():
    """Dedupe key is deterministic from task_id, date_bucket, content_hash."""
    key1 = make_dedupe_key("task-a", "2026-02-23", "abc123")
    key2 = make_dedupe_key("task-a", "2026-02-23", "abc123")
    assert key1 == key2
    assert "task-a" in key1 and "2026-02-23" in key1 and "abc123" in key1

    key3 = make_dedupe_key("task-a", "2026-02-23", "def456")
    assert key3 != key1


def test_ledger_consult_prevents_duplicate(tmp_path):
    """Before record_posted, check_already_posted returns None; after, returns existing result."""
    session = "automation-test-dedupe"
    task_id = "test-task"
    date_bucket = get_date_bucket()
    content_hash = "hash1"

    assert check_already_posted(tmp_path, session, task_id, date_bucket, content_hash) is None

    record_posted(tmp_path, session, task_id, date_bucket, content_hash, thread_id="t1", thread_url="https://x.com/t1")
    result = check_already_posted(tmp_path, session, task_id, date_bucket, content_hash)
    assert result is not None
    assert result.get("thread_id") == "t1"
    assert result.get("thread_url") == "https://x.com/t1"


# --- F2: Retry policy by class ---


@pytest.mark.skipif(get_retry_policy_for_class is None, reason="retry_policy module not yet implemented")
def test_retry_policy_by_class_transient_retryable():
    """transient_network is retryable with max_attempts > 1."""
    policy = get_retry_policy_for_class("transient_network")
    assert policy is not None
    assert policy.get("retryable") is True
    assert policy.get("max_attempts", 0) >= 2


@pytest.mark.skipif(get_retry_policy_for_class is None, reason="retry_policy module not yet implemented")
def test_retry_policy_by_class_validation_not_retryable():
    """validation_failed is not retryable."""
    policy = get_retry_policy_for_class("validation_failed")
    assert policy is not None
    assert policy.get("retryable") is False


@pytest.mark.skipif(is_retryable is None, reason="retry_policy module not yet implemented")
def test_is_retryable():
    """is_retryable returns True for retryable classes, False for non-retryable."""
    assert is_retryable("transient_network") is True
    assert is_retryable("validation_failed") is False
    assert is_retryable("safety_blocked") is False


# --- F3: DLQ replay ---


def test_terminal_failure_produces_dlq_artifact(tmp_path):
    """write_failed_run produces a JSON file with run_id, inputs, error, etc."""
    from hg_core.deadletter import write_failed_run, load_deadletter

    path = write_failed_run(
        tmp_path,
        task_id="test-task",
        run_id="run-123",
        error={"failure_class": "timeout", "message": "timed out"},
        inputs={"goal": "test"},
        outputs={},
    )
    assert path.exists()
    data = load_deadletter(path)
    assert data["run_id"] == "run-123"
    assert data["task_id"] == "test-task"
    assert data["error"]["failure_class"] == "timeout"
    assert data["inputs"]["goal"] == "test"


@pytest.mark.skipif(replay_deadletter_run is None, reason="deadletter_replay not yet implemented")
def test_dlq_replay_no_side_effects_mode(tmp_path):
    """Replay from DLQ in no-side-effects mode returns decisions without executing external writes."""
    from hg_core.deadletter import write_failed_run, load_deadletter

    write_failed_run(
        tmp_path,
        task_id="replay-task",
        run_id="run-456",
        error={"failure_class": "timeout", "message": "timed out"},
        inputs={"goal": "replay test", "seed": 42},
        outputs={"selected_topic": "ai"},
    )
    files = list_deadletter_files(tmp_path, task_id="replay-task")
    assert len(files) >= 1
    result = replay_deadletter_run(files[0], workspace_root=tmp_path, no_side_effects=True)
    assert result is not None
    assert "decisions" in result or "inputs" in result


# --- F5: Circuit breaker ---


@pytest.mark.skipif(CircuitBreaker is None, reason="circuit_breaker module not yet implemented")
def test_circuit_breaker_trips_after_n_failures(tmp_path):
    """After N failures, allow_side_effect returns False until reset or cooldown."""
    key = ("workflow-1", "dest-x")
    for _ in range(3):
        record_failure(tmp_path, workflow_id=key[0], destination=key[1])
    assert allow_side_effect(tmp_path, workflow_id=key[0], destination=key[1]) is False
    reset_breaker(tmp_path, workflow_id=key[0], destination=key[1])
    assert allow_side_effect(tmp_path, workflow_id=key[0], destination=key[1]) is True
