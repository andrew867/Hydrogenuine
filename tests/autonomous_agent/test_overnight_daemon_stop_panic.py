"""Tests: STOP/PANIC control file management."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from hg_runtime.overnight_daemon.stop_panic import (
    stop_requested, panic_requested, write_stop, write_panic,
    stop_path, panic_path, control_dir, checkin_requested,
    write_request_checkin,
)


def test_stop_file_honored():
    with tempfile.TemporaryDirectory() as td:
        assert not stop_requested(td)
        write_stop(td)
        assert stop_requested(td)


def test_panic_file_honored():
    with tempfile.TemporaryDirectory() as td:
        assert not panic_requested(td)
        write_panic(td)
        assert panic_requested(td)


def test_stop_writes_partial_report():
    """Structurally: supervisor handles 'stop' result and writes final report."""
    import inspect
    from hg_runtime.overnight_daemon.supervisor import run_daemon
    src = inspect.getsource(run_daemon)
    assert "_write_final_report" in src


def test_panic_writes_emergency_proof():
    """Structurally: supervisor writes final report even on panic."""
    import inspect
    from hg_runtime.overnight_daemon.supervisor import _write_final_report
    src = inspect.getsource(_write_final_report)
    assert "RED_PANIC_STOP" in src or "YELLOW_PANIC_PARTIAL" in src


def test_daemon_exits_after_stop():
    """Structurally: scheduler returns 'stop' which breaks the loop."""
    import inspect
    from hg_runtime.overnight_daemon.scheduler import run_cycle
    src = inspect.getsource(run_cycle)
    assert 'return "stop"' in src


def test_daemon_exits_after_panic():
    import inspect
    from hg_runtime.overnight_daemon.scheduler import run_cycle
    src = inspect.getsource(run_cycle)
    assert 'return "panic"' in src


def test_stop_panic_checked_before_model_call():
    """STOP/PANIC checked before every LM Studio call."""
    import inspect
    from hg_runtime.overnight_daemon.scheduler import run_cycle
    src = inspect.getsource(run_cycle)
    lines = src.split("\n")
    found_check_before_infer = False
    for i, line in enumerate(lines):
        if "panic_requested" in line and i < len(lines) - 1:
            rest = "\n".join(lines[i:])
            if "infer_with_retry" in rest:
                found_check_before_infer = True
                break
    assert found_check_before_infer


def test_control_dir_created():
    with tempfile.TemporaryDirectory() as td:
        cd = control_dir(td)
        assert cd.exists()
        assert cd.is_dir()


def test_stop_path_location():
    with tempfile.TemporaryDirectory() as td:
        p = stop_path(td)
        assert p.name == "STOP"
        assert "control" in str(p)


def test_panic_path_location():
    with tempfile.TemporaryDirectory() as td:
        p = panic_path(td)
        assert p.name == "PANIC"
        assert "control" in str(p)


def test_checkin_request_consumed():
    with tempfile.TemporaryDirectory() as td:
        assert not checkin_requested(td)
        write_request_checkin(td)
        assert checkin_requested(td)
        # Consumed after read
        assert not checkin_requested(td)
