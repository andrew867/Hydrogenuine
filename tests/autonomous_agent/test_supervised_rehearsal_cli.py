"""Supervised rehearsal CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.stop_panic.run_rehearsal_dir", lambda run_id, base=None: (tmp_path / "rehearsals" / run_id))
    return tmp_path


def test_cli_no_publish_send():
    text = (WORKSPACE / "scripts/dev/agent_zero_supervised_rehearsal.py").read_text(encoding="utf-8")
    for cmd in ("--publish", "--send", "--approve"):
        assert cmd not in text


def test_cli_stop_creates_file(tmp_path):
    env = {**__import__("os").environ, "HG_REHEARSAL_ROOT": str(tmp_path / "rehearsals")}
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_supervised_rehearsal.py"),
         "--run-id", "cli-stop", "--stop"],
        cwd=WORKSPACE, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"]


def test_cli_panic_creates_file(tmp_path):
    env = {**__import__("os").environ, "HG_REHEARSAL_ROOT": str(tmp_path / "rehearsals")}
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_supervised_rehearsal.py"),
         "--run-id", "cli-panic", "--panic"],
        cwd=WORKSPACE, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0


def test_cli_short_rehearsal(tmp_path):
    env = {
        **__import__("os").environ,
        "HG_REHEARSAL_ROOT": str(tmp_path / "rehearsals"),
        "HG_AGENT_TURN_BASE": str(tmp_path / "turns"),
        "HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED": "false",
        "HG_COGNITIVE_SOAK_ACTIVE": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_supervised_rehearsal.py"),
         "--run-id", "cli-run", "--agent-id", "zero", "--max-turns", "1"],
        cwd=WORKSPACE, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["turn_count"] == 1
