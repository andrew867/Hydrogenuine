from __future__ import annotations

from hg_embodied.actuator.contracts import ActuatorCommand
from hg_embodied.actuator.energy_planner import SETTLE_SAFE_RESERVE_WH, EnergyPlanner


def test_estimate_known_action():
    planner = EnergyPlanner(battery_wh=100.0)
    cmd = ActuatorCommand(command_id="c1", robot_id="r1", action="navigate")
    assert planner.estimate(cmd) == 3.0
    assert planner.estimates["c1"] == 3.0


def test_estimate_unknown_action_defaults():
    planner = EnergyPlanner(battery_wh=100.0)
    cmd = ActuatorCommand(command_id="c2", robot_id="r1", action="custom_action")
    assert planner.estimate(cmd) == 1.5


def test_available_wh_respects_reserve():
    planner = EnergyPlanner(battery_wh=10.0, consumed_wh=2.0)
    assert planner.available_wh() == 10.0 - 2.0 - SETTLE_SAFE_RESERVE_WH


def test_can_execute_ok_when_sufficient():
    planner = EnergyPlanner(battery_wh=10.0)
    cmd = ActuatorCommand(command_id="c3", robot_id="r1", action="read_sensor")
    ok, reason = planner.can_execute(cmd)
    assert ok is True
    assert reason == "ok"


def test_can_execute_refused_below_reserve():
    planner = EnergyPlanner(battery_wh=2.0)
    cmd = ActuatorCommand(command_id="c4", robot_id="r1", action="navigate")
    ok, reason = planner.can_execute(cmd)
    assert ok is False
    assert reason == "below_safety_reserve_level_4"


def test_record_consumption_updates_consumed():
    planner = EnergyPlanner(battery_wh=20.0)
    cmd = ActuatorCommand(command_id="c5", robot_id="r1", action="move_slow")
    planner.estimate(cmd)
    before = planner.available_wh()
    planner.record_consumption("c5")
    assert planner.available_wh() < before
