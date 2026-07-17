"""Phase 16 no external side effects tests."""
from __future__ import annotations

import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

FORBIDDEN = [
    "hg_runtime/live_read_endurance/live_publisher.py",
    "hg_runtime/live_read_endurance/live_sender.py",
]


def test_no_live_write_modules():
    for rel in FORBIDDEN:
        assert not (WORKSPACE / rel).exists()


def test_no_pass_stubs_in_live_read_endurance():
    pkg = WORKSPACE / "hg_runtime/live_read_endurance"
    for py in pkg.glob("*.py"):
        lines = py.read_text(encoding="utf-8").splitlines()
        assert not any(line.strip() == "pass" for line in lines), py.name


def test_env_live_writes_disabled(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.social_capability.credentials.load_operator_social_env",
        lambda **kwargs: [],
    )
    monkeypatch.setenv("HG_SOCIAL_LIVE_REPLY", "false")
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_LIVE_BROWSER_ENABLED", "false")
    monkeypatch.setenv("HG_EXTERNAL_SEND_ENABLED", "false")
    from hg_runtime.social_capability.live_bridge import live_writes_disabled

    assert live_writes_disabled() is True


def test_no_secrets_in_git_staged():
    import subprocess

    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return
    for line in proc.stdout.splitlines():
        low = line.lower()
        assert ".env" not in low
        assert ".hg-local" not in low
        assert "token" not in low or line.endswith(".example.json")
