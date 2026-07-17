"""Test that run_task does not write outside HG_WORKSPACE."""

import os
import subprocess
import sys


def test_no_writes_outside_workspace(tmp_path):
    """With HG_WORKSPACE=temp, run_task must not create files outside that dir."""
    # Workspace isolated under tmp_path
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks").mkdir(parents=True)
    # Minimal task file so run_task succeeds
    task_md = workspace / "skills" / "automation" / "tasks" / "moltbook-auto-post.md"
    task_md.write_text("# Moltbook Auto Post\n\nPost content.", encoding="utf-8")

    # Directory that must remain untouched (outside workspace)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_before = set(outside.iterdir())

    # Isolate from default workspace
    env = os.environ.copy()
    env["HG_WORKSPACE"] = str(workspace)
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
    assert result.returncode == 0, f"stderr: {result.stderr}"

    # Nothing new under "outside"
    outside_after = set(outside.iterdir())
    assert outside_before == outside_after, f"Wrote outside workspace: {outside_after - outside_before}"
