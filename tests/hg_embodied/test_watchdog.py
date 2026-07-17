from __future__ import annotations

import time
from unittest.mock import patch

from hg_embodied.actuator.conformance_checker import TraceConformanceChecker
from hg_embodied.actuator.watchdog import Watchdog, LADDER_HOLD_S, LADDER_SETTLE_S, LADDER_SLOW_S


def test_ladder_monotonicity():
    wd = Watchdog(robot_id="robot-1")
    wd.on_comms_lost()
    states = []
    with patch("hg_embodied.actuator.watchdog.time") as mock_time:
        t0 = 1000.0
        mock_time.time.return_value = t0
        wd.disconnected_at = t0
        mock_time.time.return_value = t0 + LADDER_SLOW_S + 0.1
        states.append(wd.tick())
        mock_time.time.return_value = t0 + LADDER_HOLD_S + 0.1
        states.append(wd.tick())
        mock_time.time.return_value = t0 + LADDER_SETTLE_S + 0.1
        states.append(wd.tick())
    assert states == ["slowed", "hold", "settled"]


def test_resume_requires_fresh_gate():
    wd = Watchdog(robot_id="robot-1")
    wd.state = "settled"
    assert wd.pass_resume_gate(fresh_env_model=False) is False
    assert wd.pass_resume_gate(fresh_env_model=True) is True
    assert wd.state == "nominal"


def test_trace_conformance_ladder():
    wd = Watchdog(robot_id="robot-1")
    wd.on_comms_lost()
    checker = TraceConformanceChecker()
    violations = checker.check_trace(wd.trace.all_events())
    assert violations == []


def test_actuation_blocked_when_degraded():
    wd = Watchdog(robot_id="robot-1")
    wd.state = "hold"
    wd.disconnected_at = time.time()
    assert wd.is_actuation_allowed() is False
