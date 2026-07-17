"""Tests: hourly check-ins — wall-clock based, never fabricated."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from hg_runtime.overnight_daemon.checkins import (
    checkin_due, write_checkin, future_checkin_is_fabricated,
)
from hg_runtime.overnight_daemon.state import RunState


def test_hour_00_written_on_start():
    assert checkin_due(0.0, 60, -1)


def test_hour_01_not_fabricated_before_elapsed():
    assert future_checkin_is_fabricated(1, 60.0, 60)
    assert future_checkin_is_fabricated(1, 3500.0, 60)


def test_hour_01_valid_after_elapsed():
    assert not future_checkin_is_fabricated(1, 3700.0, 60)


def test_checkin_written_when_due():
    with tempfile.TemporaryDirectory() as td:
        state = RunState(run_id="test", elapsed_seconds=100.0,
                         last_checkin_hour=-1, cycle_count=5)
        assert checkin_due(100.0, 60, -1)
        jsonl_path, md_path = write_checkin(
            state, td, daemon_pid=12345,
        )
        assert jsonl_path.exists()
        assert md_path.exists()
        assert "hour_00" in md_path.name


def test_checkin_contains_required_counts():
    with tempfile.TemporaryDirectory() as td:
        state = RunState(run_id="test", elapsed_seconds=3700.0,
                         last_checkin_hour=0, cycle_count=10,
                         retry_attempts=3, retry_successes=2, retry_failures=1)
        jsonl_path, md_path = write_checkin(
            state, td, daemon_pid=12345,
            models_used=["google/gemma-4-e4b"],
        )
        data = json.loads(jsonl_path.read_text().strip().split("\n")[-1])
        assert data["cycle_count"] == 10
        assert data["final_answer_retry_attempts"] == 3
        assert data["final_answer_retry_successes"] == 2


def test_checkin_records_model_output_classifications():
    with tempfile.TemporaryDirectory() as td:
        state = RunState(run_id="test", elapsed_seconds=100.0,
                         last_checkin_hour=-1)
        state.output_classifications["content_plus_reasoning"] = 5
        state.output_classifications["reasoning_only"] = 1
        _, md_path = write_checkin(state, td, daemon_pid=12345)
        md = md_path.read_text()
        assert "content_plus_reasoning: 5" in md
        assert "reasoning_only: 1" in md


def test_checkin_records_retry_counts():
    with tempfile.TemporaryDirectory() as td:
        state = RunState(run_id="test", elapsed_seconds=100.0,
                         last_checkin_hour=-1,
                         retry_attempts=2, retry_successes=1, retry_failures=1)
        _, md_path = write_checkin(state, td, daemon_pid=12345)
        md = md_path.read_text()
        assert "Attempts: 2" in md
        assert "Successes: 1" in md


def test_checkin_failure_marks_yellow_or_red():
    """A check-in with boundary violations should record the violation count."""
    with tempfile.TemporaryDirectory() as td:
        state = RunState(run_id="test", elapsed_seconds=100.0,
                         last_checkin_hour=-1, boundary_violations=1,
                         verdict_so_far="RED_BOUNDARY_VIOLATION")
        _, md_path = write_checkin(state, td, daemon_pid=12345)
        md = md_path.read_text()
        assert "Violations: 1" in md


def test_checkin_minute_interval():
    assert checkin_due(600.0, 10, -1)  # hour_00 at 10min interval
    assert checkin_due(600.0, 10, 0)   # hour_01 due at 600s with 10min interval
    assert not checkin_due(500.0, 10, 0)  # not yet


def test_fabricated_detection_strict():
    assert future_checkin_is_fabricated(5, 100.0, 60)
    assert future_checkin_is_fabricated(2, 7100.0, 60)
    assert not future_checkin_is_fabricated(2, 7300.0, 60)
