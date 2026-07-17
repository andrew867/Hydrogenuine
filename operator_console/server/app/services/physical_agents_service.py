"""Physical agents panel: robot state, sensors, safety gate, halt/resume."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hg_embodied.actuator.contracts import ActuatorCommand
from hg_embodied.actuator.energy_planner import EnergyPlanner
from hg_embodied.actuator.safety_gate import SafetyGate
from hg_embodied.actuator.watchdog import Watchdog
from hg_embodied.sensor_fusion.attention_allocator import AttentionAllocator
from hg_embodied.sensor_fusion.contracts import EnvironmentalModel, SensorFrame
from hg_embodied.sensor_fusion.environmental_model import EnvironmentalModelBuilder
from hg_embodied.sensor_fusion.multimodal_fuser import MultimodalFuser
from hg_embodied.sensor_fusion.thz_adapter import ConsentZone, ThzAdapter


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _PhysicalAgentsState:
    def __init__(self) -> None:
        self.seeded = False
        self.robots: Dict[str, Dict[str, Any]] = {}


_STATE = _PhysicalAgentsState()


def reset_physical_agents_state() -> None:
    _STATE.seeded = False
    _STATE.robots.clear()


def seed_physical_demo() -> Dict[str, Any]:
    robot_id = "robot-alpha"
    gate = SafetyGate(robot_id=robot_id)
    watchdog = Watchdog(robot_id=robot_id)
    builder = EnvironmentalModelBuilder(robot_id=robot_id)
    fuser = MultimodalFuser(robot_id=robot_id)
    thz = ThzAdapter(
        robot_id=robot_id,
        zones=[
            ConsentZone("zone_industrial", "industrial", [(0, 0), (20, 0), (20, 20), (0, 20)]),
            ConsentZone("zone_shared", "shared", [(20, 0), (30, 0), (30, 10), (20, 10)], consent_granted=True),
        ],
    )
    ts = _iso_now()
    fuser.ingest(SensorFrame(f"lidar_{uuid.uuid4().hex[:6]}", robot_id, "lidar", ts, "lidar://scan/latest"))
    fuser.ingest(SensorFrame(f"cam_{uuid.uuid4().hex[:6]}", robot_id, "camera", ts, "camera://rgb/latest"))
    thz_frame = thz.ingest_spectral_frame([0.3, 0.7, 0.2], {"x": 5.0, "y": 5.0})
    fuser.ingest(thz_frame)
    fused = fuser.fuse()
    env_model = builder.update_from_fusion(fused)
    energy = EnergyPlanner(battery_wh=87.5)
    alloc = AttentionAllocator()
    attention = alloc.allocate(list(fused.get("modalities", {}).keys()))

    _STATE.robots[robot_id] = {
        "robot_id": robot_id,
        "fingerprint_id": "fp_physical_demo",
        "lifecycle": "active",
        "pose": {"x": 5.0, "y": 3.0, "theta": 0.1},
        "battery_pct": 0.875,
        "safety_gate": gate,
        "watchdog": watchdog,
        "builder": builder,
        "fuser": fuser,
        "thz": thz,
        "env_model": env_model,
        "energy": energy,
        "sensing_active": True,
        "modalities": list(fused.get("modalities", {}).keys()),
        "attention_hz": attention,
        "last_heartbeat": ts,
    }
    _STATE.seeded = True
    return {"ok": True, "robot_id": robot_id, "seeded": True}


def _require_robot(robot_id: str) -> Dict[str, Any]:
    if not _STATE.seeded:
        seed_physical_demo()
    robot = _STATE.robots.get(robot_id)
    if not robot:
        return {"ok": False, "error": "robot_not_found"}
    return {"ok": True, "robot": robot}


def list_physical_agents() -> Dict[str, Any]:
    if not _STATE.seeded:
        seed_physical_demo()
    agents = []
    for rid, data in _STATE.robots.items():
        gate: SafetyGate = data["safety_gate"]
        wd: Watchdog = data["watchdog"]
        agents.append({
            "robot_id": rid,
            "fingerprint_id": data["fingerprint_id"],
            "lifecycle": data["lifecycle"],
            "pose": data["pose"],
            "battery_pct": data["battery_pct"],
            "safety_state": "halted" if gate.halted else gate.gate_state,
            "watchdog_state": wd.state,
            "sensing_active": data["sensing_active"],
            "modalities": data["modalities"],
            "last_heartbeat": data["last_heartbeat"],
        })
    return {"ok": True, "agents": agents}


def get_physical_agent(robot_id: str) -> Dict[str, Any]:
    result = _require_robot(robot_id)
    if not result.get("ok"):
        return result
    data = result["robot"]
    gate: SafetyGate = data["safety_gate"]
    wd: Watchdog = data["watchdog"]
    env: EnvironmentalModel = data["env_model"]
    builder: EnvironmentalModelBuilder = data["builder"]
    return {
        "ok": True,
        "robot_id": robot_id,
        "fingerprint_id": data["fingerprint_id"],
        "lifecycle": data["lifecycle"],
        "pose": data["pose"],
        "battery_pct": data["battery_pct"],
        "safety": {
            "state": "halted" if gate.halted else gate.gate_state,
            "halted": gate.halted,
            "pending_command": gate.pending.command.command_id if gate.pending else None,
            "recent_decisions": [d.to_dict() for d in list(gate.decisions.values())[-5:]],
            "halt_events": list(gate.halt_events[-3:]),
        },
        "watchdog": {
            "state": wd.state,
            "actuation_allowed": wd.is_actuation_allowed(),
        },
        "sensors": {
            "sensing_active": data["sensing_active"],
            "modalities": data["modalities"],
            "attention_hz": data["attention_hz"],
            "environmental_model": env.to_dict(),
            "model_stale": builder.is_stale(),
            "human_near": builder.human_within_threshold(env),
        },
        "energy": {
            "battery_wh": data["energy"].battery_wh,
            "available_wh": data["energy"].available_wh(),
            "reserve_wh": data["energy"].reserve_wh,
        },
        "last_heartbeat": data["last_heartbeat"],
    }


def halt_robot(robot_id: str, reason: str = "operator_halt") -> Dict[str, Any]:
    result = _require_robot(robot_id)
    if not result.get("ok"):
        return result
    gate: SafetyGate = result["robot"]["safety_gate"]
    event = gate.emergency_halt(reason)
    result["robot"]["lifecycle"] = "halted"
    return {"ok": True, "halt": event}


def resume_robot(robot_id: str) -> Dict[str, Any]:
    result = _require_robot(robot_id)
    if not result.get("ok"):
        return result
    gate: SafetyGate = result["robot"]["safety_gate"]
    wd: Watchdog = result["robot"]["watchdog"]
    builder: EnvironmentalModelBuilder = result["robot"]["builder"]
    if not wd.pass_resume_gate(fresh_env_model=not builder.is_stale()):
        return {"ok": False, "error": "watchdog_resume_gate_failed"}
    if not gate.resume_after_halt(operator_acknowledged=True):
        return {"ok": False, "error": "halt_resume_denied"}
    result["robot"]["lifecycle"] = "active"
    return {"ok": True, "lifecycle": "active"}


def evaluate_command(robot_id: str, action: str, *, operator_ack: bool = False) -> Dict[str, Any]:
    result = _require_robot(robot_id)
    if not result.get("ok"):
        return result
    data = result["robot"]
    gate: SafetyGate = data["safety_gate"]
    env: EnvironmentalModel = data["env_model"]
    cmd = ActuatorCommand(f"cmd_{uuid.uuid4().hex[:8]}", robot_id, action)
    decision = gate.evaluate(cmd, env, operator_ack=operator_ack)
    return {"ok": True, "command": cmd.to_dict(), "decision": decision.to_dict()}
