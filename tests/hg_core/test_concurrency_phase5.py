"""Tests for autonomy Phase 5: concurrency and scheduling (Q1–Q4)."""

import pytest
from pathlib import Path

from hg_core.task_graph.run_lock import (
    acquire_lock,
    release_lock,
    apply_jitter_sec,
)
from hg_core.task_graph.concurrency_caps import (
    try_acquire,
    release,
    set_limits,
)


# --- Q1: Distributed lock ---


def test_lock_prevents_duplicate_run(tmp_path):
    """First acquire succeeds; second acquire for same (workflow_id, time_bucket) fails until release."""
    workflow_id = "workflow-a"
    time_bucket = "2026-02-23T12"
    run_id_1 = "run-1"
    run_id_2 = "run-2"

    got1 = acquire_lock(tmp_path, workflow_id, time_bucket, run_id_1, ttl_sec=60)
    assert got1 is True

    got2 = acquire_lock(tmp_path, workflow_id, time_bucket, run_id_2, ttl_sec=60)
    assert got2 is False

    release_lock(tmp_path, workflow_id, time_bucket)
    got3 = acquire_lock(tmp_path, workflow_id, time_bucket, run_id_2, ttl_sec=60)
    assert got3 is True


# --- Q2: Concurrency caps ---


def test_concurrency_cap_global(tmp_path):
    """When global cap reached, try_acquire returns False."""
    set_limits(global_max=2, per_workflow_max=5)
    assert try_acquire("w1") is True
    assert try_acquire("w2") is True
    assert try_acquire("w3") is False
    release("w1")
    assert try_acquire("w3") is True
    release("w2")
    release("w3")


def test_concurrency_cap_per_workflow(tmp_path):
    """When per-workflow cap reached, try_acquire for same workflow returns False."""
    set_limits(global_max=10, per_workflow_max=2)
    assert try_acquire("w1") is True
    assert try_acquire("w1") is True
    assert try_acquire("w1") is False
    release("w1")
    assert try_acquire("w1") is True
    release("w1")
    release("w1")


# --- Q3: Jitter ---


def test_apply_jitter_returns_in_range():
    """apply_jitter_sec returns value within [scheduled - jitter, scheduled + jitter] (approx)."""
    for _ in range(20):
        result = apply_jitter_sec(100.0, 10.0)
        assert 90.0 <= result <= 110.0
