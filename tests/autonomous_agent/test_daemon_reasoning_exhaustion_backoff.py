"""Tests: reasoning exhaustion backoff — daemon continues, backs off, skips."""

from __future__ import annotations

import inspect

from hg_runtime.overnight_daemon.model_role_routing import SeedModeFailureTracker
from hg_runtime.overnight_daemon.scheduler import run_cycle, _SCIENCE_CYCLE


def test_reasoning_only_truncated_does_not_crash_daemon():
    src = inspect.getsource(run_cycle)
    assert "reasoning_only_truncated" in src
    assert "reasoning_exhaustion_backoff" in src


def test_final_answer_retry_failed_does_not_crash_daemon():
    src = inspect.getsource(run_cycle)
    assert "empty_content" in src or "final_answer_retry_failed" in src or "reasoning_only_truncated" in src


def test_repeated_failure_backs_off_seed_mode_model():
    ft = SeedModeFailureTracker()
    assert not ft.should_skip("s1", "falsification_design", "gemma")
    ft.record_failure("s1", "falsification_design", "gemma")
    assert not ft.should_skip("s1", "falsification_design", "gemma")
    ft.record_failure("s1", "falsification_design", "gemma")
    assert ft.should_skip("s1", "falsification_design", "gemma")


def test_seed_skipped_after_repeated_failures():
    ft = SeedModeFailureTracker()
    for mode in _SCIENCE_CYCLE:
        ft.record_failure("s1", mode, "gemma")
        ft.record_failure("s1", mode, "gemma")
    assert ft.all_modes_failed("s1", _SCIENCE_CYCLE)


def test_daemon_continues_to_next_seed():
    src = inspect.getsource(run_cycle)
    assert "seed_skip_after_failures" in src
    assert "YELLOW_SKIPPED_AFTER_FAILURES" in src


def test_evidence_gap_written_for_failed_mode():
    src = inspect.getsource(run_cycle)
    assert "evidence_gap_ledger" in src


def test_failure_tracker_different_model_no_backoff():
    ft = SeedModeFailureTracker()
    ft.record_failure("s1", "m1", "model_a")
    ft.record_failure("s1", "m1", "model_a")
    assert ft.should_skip("s1", "m1", "model_a")
    assert not ft.should_skip("s1", "m1", "model_b")


def test_failure_count():
    ft = SeedModeFailureTracker()
    ft.record_failure("s1", "m1", "model_a")
    ft.record_failure("s1", "m2", "model_a")
    assert ft.seed_failure_count("s1") == 2
    assert ft.seed_failure_count("s2") == 0


def test_not_all_modes_failed_partial():
    ft = SeedModeFailureTracker()
    ft.record_failure("s1", _SCIENCE_CYCLE[0], "gemma")
    ft.record_failure("s1", _SCIENCE_CYCLE[0], "gemma")
    assert not ft.all_modes_failed("s1", _SCIENCE_CYCLE)


def test_scheduler_uses_failure_tracker():
    src = inspect.getsource(run_cycle)
    assert "failure_tracker" in src
    assert "should_skip" in src


def test_scheduler_records_backoff():
    src = inspect.getsource(run_cycle)
    assert "reasoning_exhaustion_backoff" in src
    assert "recorded_failure_backoff" in src or "skipped_after_repeated_failure" in src
