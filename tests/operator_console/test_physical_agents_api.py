from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app
from operator_console.server.app.services import physical_agents_service as pasvc


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture(autouse=True)
def reset_physical_state():
    pasvc.reset_physical_agents_state()
    yield
    pasvc.reset_physical_agents_state()


def test_seed_and_list_agents(operator_client):
    headers = {"Authorization": "Bearer test-api-key"}
    seed = operator_client.post("/api/v1/physical/seed-demo", headers=headers, json={})
    assert seed.status_code == 200
    assert seed.json()["ok"] is True
    res = operator_client.get("/api/v1/physical/agents", headers=headers)
    assert res.status_code == 200
    agents = res.json()["agents"]
    assert len(agents) >= 1
    assert agents[0]["sensing_active"] is True


def test_halt_and_resume(operator_client):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/physical/seed-demo", headers=headers, json={})
    robot_id = "robot-alpha"
    detail = operator_client.get(f"/api/v1/physical/agents/{robot_id}", headers=headers)
    assert detail.status_code == 200
    halt = operator_client.post(f"/api/v1/physical/agents/{robot_id}/halt", headers=headers, json={"reason": "test"})
    assert halt.status_code == 200
    after_halt = operator_client.get(f"/api/v1/physical/agents/{robot_id}", headers=headers)
    assert after_halt.json()["safety"]["halted"] is True
    resume = operator_client.post(f"/api/v1/physical/agents/{robot_id}/resume", headers=headers)
    assert resume.status_code == 200
    assert resume.json()["lifecycle"] == "active"


def test_evaluate_command(operator_client):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/physical/seed-demo", headers=headers, json={})
    res = operator_client.post(
        "/api/v1/physical/agents/robot-alpha/evaluate",
        headers=headers,
        json={"action": "read_sensor"},
    )
    assert res.status_code == 200
    assert res.json()["decision"]["allowed"] is True
