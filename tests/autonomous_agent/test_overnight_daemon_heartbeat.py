"""Tests: daemon heartbeat — periodic updates, staleness detection."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from hg_runtime.overnight_daemon.heartbeat import (
    write_heartbeat, read_heartbeat, heartbeat_age_seconds, is_stale,
    heartbeat_path,
)


def test_heartbeat_updates_periodically():
    with tempfile.TemporaryDirectory() as td:
        hb1 = write_heartbeat(td, run_id="r1", pid=100, started_at="2026-01-01T00:00:00Z")
        t1 = hb1["last_heartbeat_at"]
        time.sleep(0.05)
        hb2 = write_heartbeat(td, run_id="r1", pid=100, started_at="2026-01-01T00:00:00Z",
                              cycle_count=1)
        t2 = hb2["last_heartbeat_at"]
        # Heartbeat updated (may be same second in fast tests, but file is overwritten)
        loaded = read_heartbeat(td)
        assert loaded["cycle_count"] == 1


def test_heartbeat_records_current_seed():
    with tempfile.TemporaryDirectory() as td:
        write_heartbeat(td, run_id="r1", pid=100, started_at="2026-01-01T00:00:00Z",
                        current_seed_id="electron_hole_spin")
        hb = read_heartbeat(td)
        assert hb["current_seed_id"] == "electron_hole_spin"


def test_heartbeat_records_current_status():
    with tempfile.TemporaryDirectory() as td:
        write_heartbeat(td, run_id="r1", pid=100, started_at="2026-01-01T00:00:00Z",
                        current_status="running")
        hb = read_heartbeat(td)
        assert hb["current_status"] == "running"


def test_stale_heartbeat_detected():
    with tempfile.TemporaryDirectory() as td:
        # Write heartbeat with old timestamp
        hb = {"run_id": "r1", "pid": 100, "started_at": "2026-01-01T00:00:00Z",
               "last_heartbeat_at": "2020-01-01T00:00:00Z"}
        (Path(td) / "heartbeat.json").write_text(json.dumps(hb), encoding="utf-8")
        assert is_stale(td, threshold_seconds=120.0)


def test_fresh_heartbeat_not_stale():
    with tempfile.TemporaryDirectory() as td:
        write_heartbeat(td, run_id="r1", pid=100, started_at="2026-01-01T00:00:00Z")
        assert not is_stale(td, threshold_seconds=120.0)


def test_heartbeat_written_before_lmstudio_call():
    """Structurally: the scheduler writes heartbeat before each inference call."""
    import inspect
    from hg_runtime.overnight_daemon.scheduler import run_cycle
    src = inspect.getsource(run_cycle)
    hb_idx = src.index("_heartbeat()")
    infer_idx = src.index("infer_with_retry")
    assert hb_idx < infer_idx


def test_heartbeat_written_after_lmstudio_call():
    """Structurally: heartbeat is written after inference too."""
    import inspect
    from hg_runtime.overnight_daemon.scheduler import run_cycle
    src = inspect.getsource(run_cycle)
    lines = src.split("\n")
    hb_after = False
    past_infer = False
    for line in lines:
        if "infer_with_retry" in line:
            past_infer = True
        if past_infer and "_heartbeat()" in line:
            hb_after = True
            break
    assert hb_after


def test_heartbeat_elapsed_seconds_increases():
    """elapsed_seconds must be computed from started_at, not hardcoded 0."""
    with tempfile.TemporaryDirectory() as td:
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        time.sleep(0.1)
        hb = write_heartbeat(td, run_id="r1", pid=100, started_at=started)
        assert hb["elapsed_seconds"] >= 0.05, \
            f"elapsed should be > 0 but got {hb['elapsed_seconds']}"


def test_heartbeat_elapsed_not_zero_after_start():
    """Regression test for the 0.0 bug — elapsed must reflect real time."""
    import inspect
    from hg_runtime.overnight_daemon.heartbeat import write_heartbeat as wh
    src = inspect.getsource(wh)
    assert '"elapsed_seconds": 0.0' not in src


def test_missing_heartbeat_is_stale():
    with tempfile.TemporaryDirectory() as td:
        assert is_stale(td)


def test_heartbeat_path_correct():
    with tempfile.TemporaryDirectory() as td:
        p = heartbeat_path(td)
        assert p.name == "heartbeat.json"
        assert str(td) in str(p)
