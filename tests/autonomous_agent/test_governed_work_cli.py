"""Governed work CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts/dev/agent_zero_governed_work_loop.py"


import uuid


def test_cli_smoke():
    run_id = f"cli23-{uuid.uuid4().hex[:8]}"
    proc = subprocess.run(
        [sys.executable, str(CLI), "--smoke", "--run-id", run_id, "--observed-iterations", "5"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "HG_SOCIAL_LIVE_PUBLISH": "false"},
        timeout=120,
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["dry_dispatch_recorded"]
    assert out["external_side_effect_count"] == 0
