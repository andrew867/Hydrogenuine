"""Dry autonomous loop scheduler tests."""
from __future__ import annotations

import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_autonomous_loop.scheduler import (
    SchedulerState,
    compute_sleep_seconds,
    new_scheduler_state,
    should_continue,
)
from hg_runtime.dry_autonomous_loop.schema import DryAutonomousLoopConfig


def test_should_continue_until_max_iterations():
    config = DryAutonomousLoopConfig(run_id="r1", agent_id="zero", max_iterations=3)
    state = SchedulerState(iteration=2, started_monotonic=time.monotonic())
    assert should_continue(state, config)
    state.iteration = 3
    assert not should_continue(state, config)


def test_should_continue_until_max_duration():
    config = DryAutonomousLoopConfig(run_id="r1", agent_id="zero", max_iterations=10, max_duration_seconds=30)
    state = SchedulerState(iteration=0, started_monotonic=time.monotonic() - 60)
    assert not should_continue(state, config)


def test_manual_step_sleep_is_zero():
    config = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", schedule_mode="manual_step", turn_interval_seconds=0.0
    )
    assert compute_sleep_seconds(config) == 0.0


def test_no_daemon_or_background_scheduler():
    text = (WORKSPACE / "hg_runtime/dry_autonomous_loop/scheduler.py").read_text(encoding="utf-8")
    code_lines = [
        line for line in text.splitlines()
        if not line.strip().startswith('"""') and not line.strip().startswith("'''") and '"""' not in line
    ]
    code = "\n".join(code_lines).lower()
    for forbidden in ("import subprocess", "import threading", "import multiprocessing", "import asyncio", "croniter", "apscheduler"):
        assert forbidden not in code


def test_new_scheduler_state_tracks_monotonic():
    state = new_scheduler_state()
    assert state.started_monotonic > 0
    assert state.iteration == 0
