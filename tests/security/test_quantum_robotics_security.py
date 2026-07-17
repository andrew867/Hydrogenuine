"""Consolidated quantum/robotics security regression module (P2-8)."""
from __future__ import annotations

import time

import pytest

from hg_core.consent.errors import ConsentDeniedError
from hg_core.consent.resolver import resolve_consent_class
from hg_embodied.actuator.contracts import ActuatorCommand
from hg_embodied.actuator.safety_gate import SafetyGate
from hg_embodied.sensor_fusion.contracts import EnvironmentalModel
from hg_embodied.ros_bridge.sros2_setup import build_sros2_artifacts, record_unauthenticated_halt
from hg_quantum.security.qkd_channel_model import QkdChannelModel
from hg_quantum.security.temporal_auth import TemporalAuthenticator


def test_unauthenticated_halt_fail_safe_logged(tmp_path):
    path = record_unauthenticated_halt(
        entity_id="robot-1",
        halt_command={"level": 4, "reason": "unauthenticated"},
        workspace_root=tmp_path,
    )
    assert (tmp_path / path).exists()
    content = (tmp_path / path).read_text(encoding="utf-8")
    assert "unauthenticated" in content.lower() or "halt" in content.lower()


def test_sros2_enclave_material_permissions(tmp_path):
    artifacts = build_sros2_artifacts("fp_sec", workspace_root=tmp_path, entity_ids=["ent-a"])
    perms = (tmp_path / artifacts.permissions_path).read_text(encoding="utf-8")
    assert "ent-a" in perms or "entity" in perms.lower()
    policy = (tmp_path / artifacts.governance_policy_path).read_text(encoding="utf-8")
    assert policy.strip()


def test_qkd_tamper_detection_triggers_fallback_recommendation():
    model = QkdChannelModel(max_qber=0.05)
    ch = model.open_channel(10.0)
    tamper = model.detect_tamper(ch.channel_id, observed_qber=ch.qber + 0.2)
    assert tamper["ok"] is True
    assert tamper["tampered"] is True
    assert tamper["action"] == "fallback_recommended"


def test_temporal_auth_replay_rejected():
    auth = TemporalAuthenticator()
    old_ts = time.time() - 120.0
    auth._history["ent-replay"] = [(old_ts, "payload_hash")]
    sig = auth.generate_temporal_signature("ent-replay")
    result = auth.verify_temporal_authenticity(
        {"entity_id": "ent-replay", "content_hash": "payload_hash", "ts": time.time()},
        sig,
    )
    assert result.authentic is False
    assert result.anomaly_type == "replay"


def test_consent_fail_closed_without_grant(tmp_path, monkeypatch):
    ledger_path = tmp_path / "consent.jsonl"
    monkeypatch.setenv("HG_CONSENT_LEDGER_PATH", str(ledger_path))
    from hg_core.consent import assert_recognition_consent

    with pytest.raises(ConsentDeniedError):
        assert_recognition_consent("unknown-subject", workspace_root=tmp_path)
    assert resolve_consent_class("unknown-subject", workspace_root=tmp_path) == "none"


def test_emergency_halt_blocks_actuator_commands():
    gate = SafetyGate(robot_id="robot-sec")
    cmd = ActuatorCommand("c_sec", "robot-sec", "read_sensor")
    model = EnvironmentalModel(
        model_id="env_sec",
        robot_id="robot-sec",
        zones=[],
        confidence=0.9,
        updated_at="2026-06-10T00:00:00Z",
    )
    gate.evaluate(cmd, model)
    gate.approved_commands.add(cmd.command_id)
    gate.emergency_halt("security_regression")
    assert gate.execute(cmd.command_id) is False
