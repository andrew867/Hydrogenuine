"""Pack2-07: Replay/fork return structured error when hg_core missing."""

import pytest


def test_replay_run_returns_structured_error_when_hg_core_missing():
    """When hg_core is not available, replay_run returns HG_CORE_REQUIRED with remediation."""
    from operator_console.server.app.services import replay_ops
    original = getattr(replay_ops, "_replay_available", True)
    try:
        replay_ops._replay_available = False
        out = replay_ops.replay_run("any-run-id")
        assert out.get("ok") is False
        err = out.get("error") or {}
        assert err.get("code") == "HG_CORE_REQUIRED"
        assert "hg_core" in (err.get("message") or "").lower()
        assert err.get("remediation")
    finally:
        replay_ops._replay_available = original


def test_fork_returns_structured_error_when_hg_core_missing():
    """When hg_core fork is not available, fork_from_snapshot returns HG_CORE_REQUIRED with remediation."""
    from operator_console.server.app.services import state_history_store
    original = getattr(state_history_store, "_core_fork", None)
    try:
        state_history_store._core_fork = None
        out = state_history_store.fork_from_snapshot("some-run", 0)
        assert out.get("ok") is False
        err = out.get("error") or {}
        assert err.get("code") == "HG_CORE_REQUIRED"
        assert "hg_core" in (err.get("message") or "").lower()
        assert err.get("remediation")
    finally:
        state_history_store._core_fork = original
