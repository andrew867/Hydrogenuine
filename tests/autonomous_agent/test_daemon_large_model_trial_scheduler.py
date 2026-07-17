"""Tests: large model trial scheduler integration."""

from __future__ import annotations

import inspect

from hg_runtime.overnight_daemon.scheduler import run_cycle


def test_scheduler_attempts_large_trial_after_triage_and_gemma():
    src = inspect.getsource(run_cycle)
    assert "large_model_trial" in src or "large_trial" in src
    assert "triage_outputs" in src


def test_scheduler_writes_large_trial_receipt():
    src = inspect.getsource(run_cycle)
    assert "large_model_trial_receipts" in src


def test_scheduler_skips_large_trial_if_no_triage_output():
    src = inspect.getsource(run_cycle)
    assert "not large_trial_attempted and triage_outputs" in src


def test_scheduler_does_not_retry_failed_candidate_forever():
    src = inspect.getsource(run_cycle)
    assert "large_trial_failed_models" in src


def test_scheduler_continues_after_large_trial_failure():
    src = inspect.getsource(run_cycle)
    assert "large_trial_failed_models" in src
    assert "Falsification targets" in src


def test_scheduler_writes_resource_preflight():
    src = inspect.getsource(run_cycle)
    assert "large_model_resource_preflight" in src


def test_scheduler_writes_comparison():
    src = inspect.getsource(run_cycle)
    assert "large_model_trial_comparison" in src


def test_scheduler_writes_operator_review():
    src = inspect.getsource(run_cycle)
    assert "large_model_trial_operator_review" in src


def test_scheduler_records_recommendation_no_promote():
    src = inspect.getsource(run_cycle)
    assert "recommendation_promote" in src
