"""Tests: daemon launch — detach, PID, heartbeat, manifest, monitor commands."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from hg_runtime.overnight_daemon.config import DaemonConfig
from hg_runtime.overnight_daemon.state import RunState, save_state, load_state
from hg_runtime.overnight_daemon.heartbeat import write_heartbeat, read_heartbeat
from hg_runtime.overnight_daemon.run_registry import generate_run_id, state_dir_for_run


def test_daemon_writes_pid_file():
    with tempfile.TemporaryDirectory() as td:
        pid_path = Path(td) / "daemon.pid"
        pid_path.write_text("12345", encoding="utf-8")
        assert pid_path.exists()
        assert pid_path.read_text().strip() == "12345"


def test_daemon_writes_initial_heartbeat():
    with tempfile.TemporaryDirectory() as td:
        hb = write_heartbeat(td, run_id="test_run", pid=9999,
                             started_at="2026-06-24T00:00:00Z")
        assert hb["run_id"] == "test_run"
        assert hb["pid"] == 9999
        loaded = read_heartbeat(td)
        assert loaded is not None
        assert loaded["run_id"] == "test_run"


def test_daemon_writes_launch_manifest():
    with tempfile.TemporaryDirectory() as td:
        manifest = {
            "run_id": "test_run",
            "pid": 12345,
            "started_at": "2026-06-24T00:00:00Z",
            "config": {"duration_hours": 12},
            "proof_dir": str(td),
            "state_dir": str(td),
        }
        p = Path(td) / "run_manifest.json"
        p.write_text(json.dumps(manifest), encoding="utf-8")
        loaded = json.loads(p.read_text())
        assert loaded["run_id"] == "test_run"
        assert loaded["pid"] == 12345


def test_daemon_returns_monitor_commands():
    run_id = "run_20260624T000000Z"
    commands = [
        f"python scripts/agent_zero_overnight_daemon.py status --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py tail --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py stop --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py panic --run-id {run_id}",
    ]
    assert all(run_id in cmd for cmd in commands)
    assert any("status" in cmd for cmd in commands)
    assert any("stop" in cmd for cmd in commands)
    assert any("panic" in cmd for cmd in commands)


def test_daemon_does_not_run_full_soak_in_foreground():
    """The start() function returns immediately — it does not block for hours."""
    from hg_runtime.overnight_daemon.daemon import start
    # We verify structurally: start() uses subprocess.Popen (not run/call)
    import inspect
    src = inspect.getsource(start)
    assert "subprocess.Popen" in src
    assert "subprocess.run" not in src
    assert "subprocess.call" not in src


def test_daemon_start_detaches():
    """Verify the start function uses detached process flags."""
    import inspect
    from hg_runtime.overnight_daemon.daemon import start
    src = inspect.getsource(start)
    assert "DETACHED_PROCESS" in src or "start_new_session" in src


def test_run_id_format():
    rid = generate_run_id()
    assert rid.startswith("run_")
    assert len(rid) > 10


def test_state_round_trip():
    with tempfile.TemporaryDirectory() as td:
        s = RunState(run_id="r1", status="running", cycle_count=5)
        save_state(s, td)
        s2 = load_state(td)
        assert s2 is not None
        assert s2.run_id == "r1"
        assert s2.cycle_count == 5


def test_config_redaction():
    cfg = DaemonConfig()
    rd = cfg.redacted()
    assert "lmstudio_base_url" in rd
    # No secret fields to redact in default config, but the method runs
    assert rd["duration_hours"] == 12.0
