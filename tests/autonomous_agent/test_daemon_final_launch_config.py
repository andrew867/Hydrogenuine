"""Tests: final daemon launch configuration."""

from __future__ import annotations

import inspect

from hg_runtime.overnight_daemon.config import DaemonConfig, parse_daemon_args
from hg_runtime.overnight_daemon.daemon import start
from hg_runtime.overnight_daemon.gate import run_gate
from hg_runtime.overnight_daemon.large_model_trial import default_large_trial_policy


def test_daemon_launch_enables_fast_triage():
    cfg = DaemonConfig()
    assert cfg.max_small_models >= 1


def test_daemon_launch_enables_gemma_synthesis():
    cfg = DaemonConfig()
    assert cfg.main_model == "google/gemma-4-e4b"


def test_daemon_launch_enables_large_trial_lane():
    cfg = DaemonConfig()
    assert cfg.enable_large_model_trial is True


def test_daemon_launch_requires_large_trial_if_safe():
    cfg = DaemonConfig()
    assert cfg.require_large_trial_if_safe is True


def test_daemon_launch_prints_monitor_commands():
    src = inspect.getsource(start)
    assert "monitor_commands" in src


def test_daemon_launch_does_not_block_for_full_soak():
    src = inspect.getsource(start)
    assert "Returns immediately" in start.__doc__


def test_daemon_launch_writes_pid_and_heartbeat():
    src = inspect.getsource(start)
    assert "daemon.pid" in src
    assert "heartbeat" in src


def test_daemon_launch_preserves_stop_panic():
    src = inspect.getsource(start)
    assert "stop_path" in src
    assert "panic_path" in src


def test_daemon_launch_zero_not_agi_conscious_sovereign():
    _, checks = run_gate()
    for key in ("zero_not_agi", "zero_not_conscious", "zero_not_sovereign"):
        found = [c for c in checks if c["check"] == key]
        assert found and found[0]["passed"]


def test_parse_enable_large_model_trial():
    cfg = parse_daemon_args(["--enable-large-model-trial"])
    assert cfg.enable_large_model_trial is True


def test_parse_require_large_trial_if_safe():
    cfg = parse_daemon_args(["--require-large-trial-if-safe"])
    assert cfg.require_large_trial_if_safe is True


def test_parse_no_large_model_trial():
    cfg = parse_daemon_args(["--no-large-model-trial"])
    assert cfg.enable_large_model_trial is False


def test_large_trial_policy_no_permanent_switch():
    p = default_large_trial_policy()
    assert p.main_brain_switch_allowed is False
    assert p.permanent_switch_allowed is False
