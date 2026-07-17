"""Phase 18 CLI tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_cli_preflight_safe():
    env = {k: v for k, v in os.environ.items()}
    env.pop("HG_PHASE18_ALLOW_LIVE_SMOKE", None)
    env["HG_ENABLE_LIVE_SOCIAL_WRITES"] = "false"
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_phase18_live_smoke.py"), "--preflight"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["credential_values_printed"] is False
