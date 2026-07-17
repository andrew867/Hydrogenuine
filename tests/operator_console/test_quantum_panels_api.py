from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app
from operator_console.server.app.services import quantum_panels_service as qsvc


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture(autouse=True)
def reset_quantum_state():
    qsvc.reset_quantum_panel_state()
    yield
    qsvc.reset_quantum_panel_state()


@pytest.fixture
def workspace_with_evals(tmp_path, monkeypatch):
    evals = tmp_path / "evals" / "quantum"
    evals.mkdir(parents=True)
    for name in ("planted_syndrome_outputs.json", "noise_fixtures.json", "labeled_correlation_traces.json"):
        src = Path(__file__).resolve().parents[2] / "evals" / "quantum" / name
        if src.exists():
            (evals / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    return tmp_path


def test_seed_demo_and_entanglement_graph(operator_client, workspace_with_evals):
    headers = {"Authorization": "Bearer test-api-key"}
    seed = operator_client.post("/api/v1/quantum/seed-demo", headers=headers, json={})
    assert seed.status_code == 200
    assert seed.json()["ok"] is True
    graph = operator_client.get("/api/v1/quantum/entanglement/graph", headers=headers)
    assert graph.status_code == 200
    data = graph.json()
    assert data["ok"] is True
    assert len(data["nodes"]) >= 2
    assert len(data["edges"]) >= 1


def test_noise_profiles(operator_client, workspace_with_evals):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/quantum/seed-demo", headers=headers, json={})
    res = operator_client.get("/api/v1/quantum/noise/profiles", headers=headers)
    assert res.status_code == 200
    profiles = res.json()["profiles"]
    assert profiles
    entity_id = profiles[0]["entity_id"]
    detail = operator_client.get(f"/api/v1/quantum/noise/profiles/{entity_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["profile"]["entity_id"] == entity_id


def test_syndrome_dashboard_and_correction_audit(operator_client, workspace_with_evals):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/quantum/seed-demo", headers=headers, json={})
    dash = operator_client.get("/api/v1/quantum/syndrome/dashboard", headers=headers)
    assert dash.status_code == 200
    body = dash.json()
    assert body["ok"] is True
    corrections = body.get("corrections") or []
    if not corrections:
        pytest.skip("no syndromes in fixture case")
    cid = corrections[0]["action_id"]
    approved = operator_client.post(f"/api/v1/quantum/syndrome/corrections/{cid}/approve", headers=headers)
    assert approved.status_code == 200
    result = approved.json()
    assert result["ok"] is True
    assert result.get("evidence_path")
    evidence = workspace_with_evals / result["evidence_path"]
    assert evidence.exists()
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["action"] == "approve_correction"


def test_syndrome_escalate_correction(operator_client, workspace_with_evals):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/quantum/seed-demo", headers=headers, json={})
    dash = operator_client.get("/api/v1/quantum/syndrome/dashboard", headers=headers)
    corrections = dash.json().get("corrections") or []
    pending = [c for c in corrections if c.get("status") == "pending"]
    if not pending:
        pytest.skip("no pending corrections in fixture case")
    cid = pending[0]["action_id"]
    escalated = operator_client.post(
        f"/api/v1/quantum/syndrome/corrections/{cid}/escalate",
        headers=headers,
        json={"rationale": "needs human review", "actor_id": "operator"},
    )
    assert escalated.status_code == 200
    result = escalated.json()
    assert result["ok"] is True
    assert result["correction"]["status"] == "escalated"
    assert result.get("post_action_landing") == "#/approvals"
