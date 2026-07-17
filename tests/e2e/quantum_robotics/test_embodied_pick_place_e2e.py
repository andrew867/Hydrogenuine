"""E2E: simulated pick-and-place with safety gate and sensor fusion."""
from __future__ import annotations

import time

import pytest

from hg_embodied.actuator.contracts import ActuatorCommand
from hg_embodied.actuator.safety_gate import SafetyGate
from hg_embodied.isaac_bridge.behavioral_tests import run_scenario_suite
from hg_embodied.sensor_fusion.contracts import EnvironmentalModel, SensorFrame
from hg_embodied.sensor_fusion.environmental_model import EnvironmentalModelBuilder
from hg_embodied.sensor_fusion.multimodal_fuser import MultimodalFuser

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def test_e2e_simulated_pick_and_place(proof_dir):
    gate = SafetyGate(robot_id="robot-pick-1")
    fuser = MultimodalFuser(robot_id="robot-pick-1")
    builder = EnvironmentalModelBuilder(robot_id="robot-pick-1")
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    fuser.ingest(SensorFrame("l1", "robot-pick-1", "lidar", ts, "lidar://scan"))
    fuser.ingest(SensorFrame("c1", "robot-pick-1", "camera", ts, "camera://rgb"))
    env = builder.update_from_fusion(fuser.fuse())

    read_cmd = ActuatorCommand("cmd_read", "robot-pick-1", "read_sensor")
    read_dec = gate.evaluate(read_cmd, env)
    move_cmd = ActuatorCommand("cmd_move", "robot-pick-1", "pick", safety_level_required=2)
    move_dec = gate.evaluate(move_cmd, env, operator_ack=True)

    results = run_scenario_suite(
        robot_config={"robot_id": "robot-pick-1", "entity_id": "robot-pick-1"},
        environment_config={"scene_id": "table_block"},
        entity_id="robot-pick-1",
        scenarios=[{"id": "pick_red_block", "task": "pick up red block", "expect_success": True}],
    )

    bundle = proof_dir / "pick_and_place"
    checks = [
        {"name": "sensor_read_approved", "pass": read_dec.allowed},
        {"name": "pick_approved_with_ack", "pass": move_dec.allowed},
        {"name": "behavioral_pass", "pass": results[0].passed},
        {"name": "proof_bundle_written", "pass": bool(results[0].proof_bundle_path)},
    ]
    write_proof_bundle(
        bundle,
        label="e2e_simulated_pick_and_place",
        checks=checks,
        summary_extra={"behavioral_metrics": results[0].metrics},
    )
    assert all(c["pass"] for c in checks)
