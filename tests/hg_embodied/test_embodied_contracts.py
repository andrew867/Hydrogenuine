from __future__ import annotations

import hg_embodied
from hg_embodied.actuator.contracts import ActuatorCommand, PhysicalStateHeartbeat, SafetyDecision
from hg_embodied.isaac_bridge.contracts import BehavioralTestResult, SimSession
from hg_embodied.ros_bridge.contracts import RobotIdentity
from hg_embodied.sensor_fusion.contracts import EnvironmentalModel, SensorFrame


def test_package_exports():
    assert hg_embodied.RobotIdentity is RobotIdentity
    assert hg_embodied.SafetyDecision is SafetyDecision


def test_robot_identity_roundtrip():
    ident = RobotIdentity(
        robot_id="robot-1",
        fingerprint_id="fp_abc",
        persona_id="per_1",
        instance_id="inst_1",
        ros_namespace="/hg/robot1",
        capabilities=["navigate", "manipulate"],
    )
    assert RobotIdentity.from_dict(ident.to_dict()) == ident


def test_sensor_and_environment_roundtrip():
    frame = SensorFrame(
        frame_id="fr1",
        robot_id="robot-1",
        modality="thz",
        timestamp="2026-06-09T00:00:00Z",
        data_ref="artifacts/thz/frame1.bin",
        consent_zone_id="industrial",
    )
    model = EnvironmentalModel("env1", "robot-1", zones=[{"id": "z1"}], confidence=0.7)
    assert SensorFrame.from_dict(frame.to_dict()) == frame
    assert EnvironmentalModel.from_dict(model.to_dict()).model_id == "env1"


def test_actuator_contracts_roundtrip():
    hb = PhysicalStateHeartbeat(
        robot_id="robot-1",
        fingerprint_id="fp_abc",
        timestamp="2026-06-09T00:00:00Z",
        pose={"x": 1.0},
        safety_level=1,
    )
    cmd = ActuatorCommand("cmd1", "robot-1", "move_base", {"x": 1.0}, safety_level_required=2)
    decision = SafetyDecision("sd1", "robot-1", 2, False, "stale sensors")
    assert PhysicalStateHeartbeat.from_dict(hb.to_dict()).robot_id == "robot-1"
    assert ActuatorCommand.from_dict(cmd.to_dict()) == cmd
    assert SafetyDecision.from_dict(decision.to_dict()) == decision


def test_isaac_contracts_roundtrip():
    session = SimSession("sess1", "warehouse_empty", "robot-1", "running")
    result = BehavioralTestResult("bt1", "sess1", True, {"success_rate": 1.0}, proof_bundle_path="docs/proofs/embodied/bt1")
    assert SimSession.from_dict(session.to_dict()) == session
    assert BehavioralTestResult.from_dict(result.to_dict()).passed is True
