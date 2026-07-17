from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def spectrum_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    return tmp_path


def test_spectrum_seed_and_snapshot(operator_client, spectrum_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    seed = operator_client.post("/api/v1/quantum/spectrum/seed-demo", headers=headers)
    assert seed.status_code == 200
    body = seed.json()
    assert body["ok"] is True
    assert body["ingested"] >= 10
    snap = operator_client.get("/api/v1/quantum/spectrum/snapshot", headers=headers)
    assert snap.status_code == 200
    assert snap.json()["snapshot"]["observation_count"] >= 10
    emitters = operator_client.get("/api/v1/quantum/spectrum/emitters", headers=headers)
    assert emitters.status_code == 200
    assert len(emitters.json()["emitters"]) >= 3
    detail = operator_client.get("/api/v1/quantum/spectrum/emitters/ent_alpha", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["emitter_id"] == "ent_alpha"
