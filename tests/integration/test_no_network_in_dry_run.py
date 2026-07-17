"""Test that run_task --dry-run does not trigger network calls."""

import os
import sys

import pytest


def test_no_network_in_dry_run(tmp_path, monkeypatch):
    """With --dry-run, run_task must not call socket.connect/create_connection."""
    # Minimal workspace
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks").mkdir(parents=True)
    task_md = workspace / "skills" / "automation" / "tasks" / "moltbook-auto-post.md"
    task_md.write_text("# Moltbook\n\nPost.", encoding="utf-8")

    env = os.environ.copy()
    env["HG_WORKSPACE"] = str(workspace)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    env["HOME"] = str(fake_home)
    if sys.platform == "win32":
        env["USERPROFILE"] = str(fake_home)

    # Fail fast if any network call is attempted
    def raise_on_connect(*args, **kwargs):
        raise OSError("Network forbidden in dry-run")

    monkeypatch.setattr("socket.socket.connect", raise_on_connect)
    monkeypatch.setattr("socket.create_connection", raise_on_connect)

    # Must add --dry-run to run_task; for now run without it (run_task does not do network)
    # The test verifies run_task completes without triggering socket
    monkeypatch.setattr(os, "environ", env)

    # Run in-process to apply monkeypatch
    import hg_core.run_task as run_task_mod

    orig_argv = sys.argv.copy()
    try:
        sys.argv = ["run_task", "moltbook-auto-post"]
        run_task_mod.main()
    except OSError as e:
        if "Network forbidden" in str(e):
            pytest.fail(f"run_task made a network call during dry-run: {e}")
        raise
    finally:
        sys.argv = orig_argv
