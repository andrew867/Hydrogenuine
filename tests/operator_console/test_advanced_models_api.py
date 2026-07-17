from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app
from operator_console.server.app.services import advanced_models_service as amsvc


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture(autouse=True)
def reset_state():
    amsvc.reset_advanced_models_state()
    yield
    amsvc.reset_advanced_models_state()


def test_seed_and_dashboard(operator_client):
    headers = {"Authorization": "Bearer test-api-key"}
    seed = operator_client.post("/api/v1/advanced-models/seed-demo", headers=headers, json={})
    assert seed.status_code == 200
    assert seed.json()["ok"] is True
    dash = operator_client.get("/api/v1/advanced-models/dashboard", headers=headers)
    assert dash.status_code == 200
    data = dash.json()
    assert len(data["models"]) == 7
    assert data["recommendations"]


def test_model_detail(operator_client):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/advanced-models/seed-demo", headers=headers, json={})
    res = operator_client.get("/api/v1/advanced-models/models/varifocal_router", headers=headers)
    assert res.status_code == 200
    assert res.json()["model"]["model_id"] == "varifocal_router"
