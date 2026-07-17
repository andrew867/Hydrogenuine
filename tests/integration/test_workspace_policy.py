"""Test workspace root policy: without sentinel or env, CLI fails with clear message."""

import os
import subprocess
import sys


def test_run_task_fails_without_workspace(tmp_path):
    """Run run_task from dir without sentinel; HG_WORKSPACE points to nonexistent path."""
    env = os.environ.copy()
    env.pop("HG_WORKSPACE", None)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    env["HOME"] = str(fake_home)
    if sys.platform == "win32":
        env["USERPROFILE"] = str(fake_home)
    result = subprocess.run(
        [sys.executable, "-m", "hg_core.run_task", "moltbook-auto-post"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode != 0
    out = result.stdout + result.stderr
    assert "HG_WORKSPACE" in out or ".hg_root" in out or "WORKSPACE" in out.upper()
