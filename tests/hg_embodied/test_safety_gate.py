from __future__ import annotations

import time

import pytest

from hg_embodied.actuator.conformance_checker import TraceConformanceChecker
from hg_embodied.actuator.safety_gate import SafetyGate
from hg_embodied.actuator.contracts import ActuatorCommand
from hg_embodied.sensor_fusion.contracts import EnvironmentalModel


def _model(*, human: bool = False, stale: bool = False) -> EnvironmentalModel:
    zones = []
    if human:
        zones.append({"human_within_threshold": True, "distance_m": 0.5})
    updated = "1970-01-01T00:00:00Z" if stale else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return EnvironmentalModel(
        model_id="env_test",
        robot_id="robot-1",
        zones=zones,
        confidence=0.9 if not stale else 0.0,
        updated_at=updated,
    )


def test_safety_gate_approves_low_risk():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c1", "robot-1", "read_sensor")
    decision = gate.evaluate(cmd, _model())
    assert decision.allowed is True
    assert decision.level == 0
    assert decision.reason == "auto-approved"


def test_safety_gate_requires_ack_for_medium_risk():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c2", "robot-1", "move_arm", safety_level_required=2)
    decision = gate.evaluate(cmd, _model())
    assert decision.allowed is False
    assert decision.level == 2
    assert "operator_ack" in decision.reason


def test_safety_gate_blocks_near_human():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c3", "robot-1", "move_arm")
    decision = gate.evaluate(cmd, _model(human=True))
    assert decision.allowed is False
    assert decision.level == 3
    assert decision.reason == "human_proximity"


def test_emergency_halt_stops_execution():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c4", "robot-1", "read_sensor")
    gate.evaluate(cmd, _model())
    gate.approved_commands.add(cmd.command_id)
    event = gate.emergency_halt("test_halt")
    assert event["reason"] == "test_halt"
    assert gate.execute(cmd.command_id) is False


def test_safety_gate_blocks_when_sensors_offline():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c5", "robot-1", "read_sensor")
    decision = gate.evaluate(cmd, _model(stale=True))
    assert decision.allowed is False
    assert decision.reason == "stale_environmental_model"


def test_execute_requires_approval_sg1():
    gate = SafetyGate(robot_id="robot-1")
    assert gate.execute("unknown") is False
    gate.approved_commands.add("approved-cmd")
    assert gate.execute("approved-cmd") is True
    assert gate.execute("approved-cmd") is False  # idempotent


def test_monotone_escalation_sg4():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c6", "robot-1", "move_arm")
    gate.evaluate(cmd, _model())
    gate.escalate(cmd.command_id, 3)
    assert gate.pending is not None
    assert gate.pending.required_level == 3


def test_halt_stress_under_100ms():
    gate = SafetyGate(robot_id="robot-1")
    start = time.perf_counter()
    for _ in range(500):
        gate.emergency_halt("stress")
        gate.resume_after_halt(operator_acknowledged=True)
        gate.halted = False
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 1000, f"halt loop too slow: {elapsed_ms}ms"


def test_trace_conformance_on_evaluate():
    gate = SafetyGate(robot_id="robot-1")
    cmd = ActuatorCommand("c7", "robot-1", "read_sensor")
    gate.evaluate(cmd, _model())
    checker = TraceConformanceChecker()
    violations = checker.check_trace(gate.trace.all_events())
    assert violations == []
