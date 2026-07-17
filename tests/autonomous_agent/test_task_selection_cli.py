"""Task selection CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts/dev/agent_zero_task_selection.py"


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env={
            **dict(__import__("os").environ),
            "HG_SOCIAL_LIVE_PUBLISH": "false",
            "HG_ENABLE_LIVE_SOCIAL_WRITES": "false",
        },
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_cli_status():
    out = _run("--status")
    assert out["phase"] == 21
    assert out["live_writes_allowed"] is False


def test_cli_seed_and_select():
    _run("--seed-demo-objectives")
    out = _run("--select-next", "--run-id", "test-cli")
    assert "verdict" in out
    assert out.get("selected") is not None or out["verdict"].startswith("GREEN_")


def test_cli_refuse():
    out = _run("--refuse-out-of-scope", "--run-id", "test-refuse")
    assert out["refused"]


def test_cli_idle():
    out = _run("--idle", "--run-id", "test-idle")
    assert out["receipt"]
