import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    TestClient = None
    app = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_ENV", "test")
    return TestClient(app)


def test_governance_contracts_and_receipt_export(client):
    contracts = client.get("/api/v1/governance/contracts", headers=_headers())
    assert contracts.status_code == 200
    assert "receipt" in contracts.json()["contracts"]

    policy = client.post(
        "/api/v1/governance/policies/versions",
        headers=_headers(),
        json={
            "policy_key": "approval_policy",
            "title": "Approval Policy",
            "category": "approval",
            "description": "Test policy",
            "content": {"required_flags": ["human_review"]},
            "rationale": "Test",
            "change_summary": "Initial",
        },
    )
    assert policy.status_code == 200
    receipts = client.get("/api/v1/governance/receipts", headers=_headers())
    receipt_id = receipts.json()["receipts"][0]["receipt_id"]
    exported = client.get(f"/api/v1/governance/receipts/{receipt_id}/export", headers=_headers())
    assert exported.status_code == 200
    assert exported.json()["verification"]["verification_status"] == "verified"


def test_governance_research_sync_api(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.governance.sync_workspace",
        lambda tenant_id, chat_id, actor_id=None: {"chat_id": chat_id, "synced_runs": 1, "workspace": {"runs": [{"message_id": "m1"}]}},
    )
    response = client.post("/api/v1/governance/research/workspaces/chat-1/sync", headers=_headers(), json={"actor_id": "operator"})
    assert response.status_code == 200
    assert response.json()["synced_runs"] == 1
