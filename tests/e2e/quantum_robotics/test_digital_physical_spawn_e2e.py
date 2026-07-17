"""E2E: digital entity spawns simulated physical subtask via HGEntityNode."""
from __future__ import annotations

import pytest

from hg_embodied.actuator.command_translator import CommandTranslator
from hg_embodied.ros_bridge.lifecycle_bridge import HgEntityState
from hg_embodied.ros_bridge.node_adapter import HGEntityNode
from hg_embodied.ros_bridge.transport import MockRosTransport

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def test_e2e_digital_to_physical_subtask_spawn(proof_dir):
    transport = MockRosTransport()
    node = HGEntityNode("digital-ent-1", "per-digital-1", "fp_e2e", transport=transport)
    node.configure()
    node.activate()
    translator = CommandTranslator(robot_id="robot-alpha")
    mesh_intent = {
        "action": "navigate",
        "command_id": "phys-subtask-1",
        "parameters": {"target": {"x": 1.0, "y": 2.0}},
        "safety_level_required": 2,
    }
    cmd = translator.from_mesh_intent(mesh_intent)
    ros_goal = translator.to_ros_goal(cmd)

    bundle = proof_dir / "digital_physical_spawn"
    checks = [
        {"name": "node_active", "pass": node.hg_state == HgEntityState.ACTIVE},
        {"name": "command_translated", "pass": cmd.action == "navigate"},
        {"name": "ros_goal_shape", "pass": ros_goal["goal_id"] == "phys-subtask-1"},
        {"name": "mesh_topics_mapped", "pass": len(node.topic_mapper.all_ros_topics()) >= 4},
    ]
    write_proof_bundle(bundle, label="e2e_digital_physical_spawn", checks=checks)
    node.deactivate()
    assert all(c["pass"] for c in checks)
