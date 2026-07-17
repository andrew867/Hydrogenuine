"""Transient cleanup tests."""

from __future__ import annotations

import time
from pathlib import Path

from hg_runtime.wake_refresh.boot_hygiene import is_protected_path, is_allowed_transient
from hg_runtime.wake_refresh.stale_locks import detect_stale_locks
from hg_runtime.wake_refresh.transient_cleanup import scan_transient


def test_protected_proof():
    blocked, _ = is_protected_path("docs/proofs/foo/bar.json")
    assert blocked is True


def test_allowed_tmp():
    assert is_allowed_transient(".hg-local/tmp/stale.cache") is True


def test_audio_runtime_venv_protected():
    blocked, reason = is_protected_path(".hg-local/audio_runtime/venv/Scripts/python.exe")
    assert blocked is True
    assert "audio_runtime/venv" in reason or "preserved" in reason


def test_stale_lock_detected(tmp_path):
    lock_dir = tmp_path / ".hg-local" / "runtime_locks"
    lock_dir.mkdir(parents=True)
    lock_file = lock_dir / "old.lock"
    lock_file.write_text("x", encoding="utf-8")
    old = time.time() - 7200
    import os
    os.utime(lock_file, (old, old))
    findings = detect_stale_locks(workspace=tmp_path, max_age_seconds=3600)
    assert len(findings) >= 1


def test_config_deletion_blocked(tmp_path):
    cfg = tmp_path / "configs" / "foo.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{}", encoding="utf-8")
    from hg_runtime.wake_refresh.waste_elimination import attempt_cleanup_path
    ok, _ = attempt_cleanup_path(cfg, workspace=tmp_path)
    assert ok is False
