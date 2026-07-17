"""Test that root-level shims print deprecation and accept --help."""

import subprocess
import sys
from pathlib import Path


def test_overseer_main_help_exit_zero():
    """python overseer_main.py --help exits 0 with deprecation message."""
    workspace = Path(__file__).parent.parent.parent
    result = subprocess.run(
        [sys.executable, "overseer_main.py", "--help"],
        capture_output=True,
        text=True,
        cwd=str(workspace),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "deprecated" in result.stderr.lower() or "deprecation" in result.stderr.lower()
