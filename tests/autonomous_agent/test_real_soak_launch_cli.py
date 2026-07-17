"""Real soak CLI tests."""
import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts/dev/agent_zero_real_soak_launch.py"


def test_cli_template_max_zero(tmp_path):
    out = tmp_path / "template.json"
    r = subprocess.run(
        [sys.executable, str(CLI), "--template-moltbook-envelope", "--soak-id", "cli-t", "--output", str(out)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["max_live_posts"] == 0
    assert out.is_file()


def test_cli_preflight():
    r = subprocess.run(
        [sys.executable, str(CLI), "--preflight", "--soak-id", "cli-pf"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["credential_values_exposed"] is False
