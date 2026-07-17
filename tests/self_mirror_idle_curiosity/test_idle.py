"""Idle curiosity bounded tests."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.idle_curiosity import IdleCuriosityConfig, run_idle_self_check


def test_idle_disabled_by_default():
    result = run_idle_self_check(IdleCuriosityConfig(enabled=False))
    assert result.started is False
    assert "DISABLED" in result.stopped_reason


def test_idle_bounded():
    result = run_idle_self_check(IdleCuriosityConfig(enabled=True, max_tasks=2, max_duration_seconds=30))
    assert result.tasks_run <= 2


def test_idle_panic_stops():
    result = run_idle_self_check(IdleCuriosityConfig(enabled=True, max_tasks=5), panic=True)
    assert result.stopped_reason == "panic"
