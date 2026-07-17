from __future__ import annotations

import pytest

from hg_embodied.isaac_bridge.sim_connector import MockIsaacSimConnector


def test_create_digital_twin_mock_session():
    conn = MockIsaacSimConnector()
    session = conn.create_digital_twin(
        {"robot_id": "robot-1"},
        {"scene_id": "table_block"},
    )
    assert session.status == "running"
    assert session.scene_id == "table_block"


def test_run_behavioral_test_records_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    conn = MockIsaacSimConnector()
    session = conn.create_digital_twin({"robot_id": "r1"}, {"scene_id": "empty_room"})
    result = conn.run_behavioral_test(
        session,
        "ent-1",
        {"id": "pick", "task": "pick up red block", "expect_success": True},
    )
    assert result.passed is True
    assert result.metrics["task_completion"] == 1.0
    assert result.proof_bundle_path
    assert (tmp_path / result.proof_bundle_path).exists()


def test_sim_session_cleanup_on_failure():
    conn = MockIsaacSimConnector()
    session = conn.create_digital_twin({"robot_id": "r1"}, {"scene_id": "empty_room"})
    sid = session.session_id
    with pytest.raises(RuntimeError):
        conn.run_behavioral_test(session, "ent-1", {"inject_failure": True})
    conn.cleanup_session(sid)
    assert sid not in conn.sessions
