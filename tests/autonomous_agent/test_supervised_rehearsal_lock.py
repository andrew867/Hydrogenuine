"""Supervised rehearsal run lock tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.supervised_rehearsal.errors import RehearsalLockError
from hg_runtime.supervised_rehearsal.run_lock import (
    LOCK_STALE_SECONDS,
    acquire_lock,
    heartbeat_lock,
    lock_state,
    read_lock,
    recover_stale_lock,
    release_lock,
)


@pytest.fixture
def lock_env(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path)
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path)
    return tmp_path


def test_acquire_and_release(lock_env):
    acquire_lock("run-a", base=lock_env)
    assert lock_state(base=lock_env).value == "active"
    release_lock("run-a", base=lock_env)
    assert read_lock(base=lock_env) is None


def test_second_run_rejected(lock_env):
    acquire_lock("run-a", base=lock_env)
    with pytest.raises(RehearsalLockError):
        acquire_lock("run-b", base=lock_env)
    release_lock("run-a", base=lock_env)


def test_heartbeat_updates(lock_env):
    acquire_lock("run-a", base=lock_env)
    before = read_lock(base=lock_env).heartbeat_at
    heartbeat_lock("run-a", base=lock_env)
    after = read_lock(base=lock_env).heartbeat_at
    assert after >= before


def test_stale_lock_detected(lock_env, monkeypatch):
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.LOCK_STALE_SECONDS", 0)
    acquire_lock("run-a", base=lock_env)
    import time
    time.sleep(0.01)
    lock = read_lock(base=lock_env)
    assert lock.state.value == "stale"
    assert recover_stale_lock(base=lock_env)
    assert read_lock(base=lock_env) is None
