from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def validation_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(tmp_path / "corpus.sqlite3"))
    monkeypatch.setenv("Q2_PRODUCTION_SHADOW_BATCH_COUNT", "2")
    monkeypatch.setenv("Q2_PRODUCTION_VALIDATION_BATCH_COUNT", "8")
    monkeypatch.setenv("HG_LEARNING_CONTROL_GROUP_ENABLED", "true")
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    return tmp_path


def test_validation_status_before_live(operator_client, validation_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    status = operator_client.get("/api/v1/quantum2/validation/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["readiness"]["ok"] is False


def test_validation_run_after_live_activation(operator_client, validation_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/quantum2/activation/run-shadow-workloads", headers=headers)
    operator_client.post(
        "/api/v1/quantum2/activation/flip-shadow-first-live",
        headers=headers,
        json={"actor_id": "operator", "rationale": "validation gate"},
    )
    operator_client.post(
        "/api/v1/quantum2/activation/flip-codec-live",
        headers=headers,
        json={"actor_id": "operator", "rationale": "validation gate"},
    )
    run = operator_client.post("/api/v1/quantum2/validation/run", headers=headers)
    assert run.status_code == 200
    body = run.json()
    assert body["ok"] is True
    report = operator_client.get("/api/v1/quantum2/validation/divergence-report", headers=headers)
    assert report.status_code == 200
    assert report.json()["ok"] is True
