"""Overnight field run CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts/dev/agent_zero_overnight_field_run.py"


def test_cli_status():
    env = {**dict(__import__("os").environ), "HG_HANDS_OFF_FAST_TURNS": "1"}
    r = subprocess.run(
        [sys.executable, str(CLI), "--status", "--field-run-id", "cli-status-test"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["foreground"] is True
    assert data["daemon"] is False
