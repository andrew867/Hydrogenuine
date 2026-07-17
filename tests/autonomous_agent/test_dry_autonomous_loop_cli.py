"""Dry autonomous loop CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts/dev/agent_zero_bounded_dry_loop.py"


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    env = {
        **dict(__import__("os").environ),
        "HG_DRY_AUTONOMOUS_LOOP_ROOT": str(tmp_path / "loop"),
        "HG_AGENT_TURN_BASE": str(tmp_path / "turns"),
        "HG_SOCIAL_LIVE_PUBLISH": "false",
        "HG_COGNITIVE_SOAK_ACTIVE": "1",
        "HG_COGNITIVE_SOAK_MODE": "bounded_dry_autonomous",
    }
    return env


def test_cli_no_publish_send():
    text = CLI.read_text(encoding="utf-8")
    for cmd in ("--publish", "--send", "--approve"):
        assert cmd not in text


def test_cli_status_read_only(cli_env):
    proc = subprocess.run(
        [sys.executable, str(CLI), "--run-id", "missing", "--status"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env=cli_env,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["run_id"] == "missing"
    assert "lock_state" in payload


def test_cli_stop_creates_file(cli_env, tmp_path):
    proc = subprocess.run(
        [sys.executable, str(CLI), "--run-id", "cli-stop", "--stop"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env=cli_env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"]
    assert (tmp_path / "loop" / "cli-stop" / "STOP").is_file() or Path(data["stop_file"]).is_file()


def test_cli_panic_creates_file(cli_env, tmp_path):
    proc = subprocess.run(
        [sys.executable, str(CLI), "--run-id", "cli-panic", "--panic"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env=cli_env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"]
    assert (tmp_path / "loop" / "cli-panic" / "PANIC").is_file() or Path(data["panic_file"]).is_file()
