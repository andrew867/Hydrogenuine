from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "oss-redteam-key")
    monkeypatch.setenv("HG_COMMUNITY_DATA_DIR", str(tmp_path / "community"))
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    from hg_gateway.main import app

    return TestClient(app), {"x-api-key": "oss-redteam-key"}, tmp_path


def test_document_ingest_does_not_write_traversal_path(tmp_path, monkeypatch) -> None:
    client, headers, root = _client(tmp_path, monkeypatch)
    response = client.post(
        "/v1/documents",
        headers=headers,
        json={"name": "../outside.md", "content": "safe local content"},
    )
    assert response.status_code == 200
    assert not (root / "outside.md").exists()
    assert response.json()["document"]["name"] == "../outside.md"


def test_expired_lease_cannot_run_tool(tmp_path, monkeypatch) -> None:
    client, headers, _ = _client(tmp_path, monkeypatch)
    lease = client.post("/v1/leases", headers=headers, json={"capability": "simulated.echo", "scope": {"local": True}})
    assert lease.status_code == 200
    lease_id = lease.json()["lease"]["lease_id"]
    assert client.post(f"/v1/leases/{lease_id}/approve", headers=headers).status_code == 200
    assert client.post(f"/v1/leases/{lease_id}/expire", headers=headers).status_code == 200
    denied = client.post("/v1/tools/simulated.echo/run", headers=headers, json={"input": "should not run"})
    assert denied.status_code == 403
    assert denied.json()["receipt"]["decision"] == "denied"


def test_memory_authority_and_receipt_chain_survive_malicious_text(tmp_path, monkeypatch) -> None:
    client, headers, _ = _client(tmp_path, monkeypatch)
    payload = "<script>fetch('/secret')</script>\n../../private"
    memory = client.post("/v1/memory", headers=headers, json={"text": payload})
    assert memory.status_code == 200
    record = memory.json()["memory"]
    assert record["authority"] == "none"
    assert record["text"] == payload

    plan = client.post("/v1/plans", headers=headers, json={"request": payload})
    plan_id = plan.json()["plan"]["plan_id"]
    approved = client.post(f"/v1/plans/{plan_id}/approve", headers=headers)
    assert approved.status_code == 200
    receipts = client.get("/v1/receipts", headers=headers).json()["receipts"]
    hashes = [receipt["receipt_hash"] for receipt in receipts]
    assert len(hashes) == len(set(hashes))
    for index, receipt in enumerate(receipts[1:], start=1):
        assert receipt["prior_hash"] == receipts[index - 1]["receipt_hash"]


def test_unknown_routes_and_tools_fail_closed(tmp_path, monkeypatch) -> None:
    client, headers, _ = _client(tmp_path, monkeypatch)
    assert client.get("/v1/workflows/not-real", headers=headers).status_code == 404
    denied = client.post("/v1/tools/native.shell/run", headers=headers, json={"cmd": "echo unsafe"})
    assert denied.status_code == 403
