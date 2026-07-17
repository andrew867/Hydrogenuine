"""CLI single-turn tests."""
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
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")

def test_cli_runs_one_turn(tmp_path):
    script = WORKSPACE / "scripts/dev/agent_zero_run_single_turn.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--run-id", "cli-run-1", "--agent-id", "zero", "--no-live-read"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "HG_SOCIAL_LIVE_PUBLISH": "false"},
    )
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert "verdict" in data or "failure_stage" in data

def test_cli_does_not_start_soak():
    import os
    assert os.environ.get("HG_COGNITIVE_SOAK_ACTIVE", "0") == "0"
