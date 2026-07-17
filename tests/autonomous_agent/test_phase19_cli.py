"""Phase 19 CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_cli_preflight():
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_phase19_external_action_audit.py"), "--preflight"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["credential_values_printed"] is False
    assert data["phase"] == 19
