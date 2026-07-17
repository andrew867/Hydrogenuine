from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app
from operator_console.server.app.services.proof_reconstruction_service import reset_proof_reconstruction_state


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_proof_reconstruction_state()
    yield
    reset_proof_reconstruction_state()


def test_seed_and_dashboard(operator_client):
    headers = {"Authorization": "Bearer test-api-key"}
    seed = operator_client.post("/api/v1/proof-reconstruction/seed-demo", headers=headers, json={})
    assert seed.status_code == 200
    assert seed.json()["ok"] is True
    dash = operator_client.get("/api/v1/proof-reconstruction/dashboard", headers=headers)
    assert dash.status_code == 200
    body = dash.json()
    assert body["ok"] is True
    assert body["event_count"] >= 4
