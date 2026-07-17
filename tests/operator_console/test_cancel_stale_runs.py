"""Tests for cancel-stale / cancel-all-active runs."""

import os
import tempfile
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    import sys

    sys.path.insert(0, str(_server_path))


@pytest.fixture
def gateway_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", path)
    from hg_gateway.db import get_connection

    with get_connection() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, graph_id TEXT, status TEXT, started_at REAL, ended_at REAL,
                run_dir TEXT, correlation_id TEXT, blocked_reason TEXT, pending_request_json TEXT)"""
        )
        c.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
            ("run-active", "social-media", "running", 1.0, None, "/tmp/run-active", None, None, None),
        )
        c.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
            ("run-gate-stub", "overseer-monitor", "blocked", 2.0, None, None, None, "missing demo backup", "{}"),
        )
        c.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
            ("run-done", "social-media", "completed", 3.0, 4.0, "/tmp/run-done", None, None, None),
        )
        for idx in range(50):
            c.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    f"noise-{idx}",
                    "social-media",
                    "blocked",
                    float(100 + idx),
                    None,
                    None,
                    None,
                    "missing demo backup",
                    "{}",
                ),
            )
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_list_cancellable_run_ids_only_returns_real_active_runs(gateway_db):
    from operator_console.server.app.services.run_index_db import list_cancellable_run_ids

    ids = list_cancellable_run_ids(stale_minutes=0)
    assert ids == ["run-active"]


def test_cancel_stale_runs_cancels_active_rows(gateway_db):
    from operator_console.server.app.services.replay_ops import cancel_stale_runs
    from operator_console.server.app.services.run_index_db import get_run

    result = cancel_stale_runs(stale_minutes=0)
    assert result["ok"] is True
    assert result["count"] == 52
    assert result["stub_cancelled"] == 51
    assert result["active_cancelled"] == 1
    assert get_run("run-active")["status"] == "cancelled"
    assert get_run("run-gate-stub")["status"] == "cancelled"
    assert get_run("run-done")["status"] == "completed"
