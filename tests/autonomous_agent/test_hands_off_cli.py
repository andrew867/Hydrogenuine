"""Hands-off CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts/dev/agent_zero_hands_off_session.py"


def _run(*args: str, timeout: int = 120) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env={
            **dict(__import__("os").environ),
            "HG_SOCIAL_LIVE_PUBLISH": "false",
            "HG_ENABLE_LIVE_SOCIAL_WRITES": "false",
            "HG_HANDS_OFF_FAST_TURNS": "1",
        },
        timeout=timeout,
    )
    try:
        body = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        body = {"raw": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, body


def test_cli_test_start():
    code, out = _run(
        "--start",
        "--session-id",
        "cli-test-22",
        "--test-stop-after-observed-turns",
        "2",
        timeout=180,
    )
    assert out.get("turn_count", 0) >= 2 or code == 0


def test_cli_stop_file():
    _run("--start", "--session-id", "cli-stop-test", "--test-stop-after-observed-turns", "1", timeout=180)
    code, out = _run("--stop", "--session-id", "cli-stop-test")
    assert code == 0
    assert "stop_file" in out
