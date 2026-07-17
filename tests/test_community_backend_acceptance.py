from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


def _client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "oss-test-key")
    monkeypatch.setenv("HG_COMMUNITY_DATA_DIR", str(tmp_path / "community"))
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    from hg_gateway.main import app

    return TestClient(app), {"x-api-key": "oss-test-key"}


def test_community_backend_acceptance_flow(tmp_path, monkeypatch):
    client, headers = _client(tmp_path, monkeypatch)

    assert client.get("/healthz").status_code == 200
    diagnostics = client.get("/v1/diagnostics", headers=headers)
    assert diagnostics.status_code == 200
    assert diagnostics.json()["telemetry"] == "off"

    models = client.get("/v1/models", headers=headers).json()["providers"]
    assert {provider["id"] for provider in models} >= {"stub", "openai-compatible", "ollama", "lm-studio", "vllm"}
    assert all(provider["authority_effect"] == "none" for provider in models)

    chat = client.post("/v1/chats", headers=headers, json={"title": "Acceptance chat"})
    assert chat.status_code == 200
    chat_id = chat.json()["chat_id"]
    message = client.post(f"/v1/chats/{chat_id}/messages", headers=headers, json={"content": "Plan a cited local research task.", "provider": "stub"})
    assert message.status_code == 200
    stream = client.post(f"/v1/chats/{chat_id}/messages/stream", headers=headers, json={"content": "Stream a concise update.", "provider": "stub"})
    assert stream.status_code == 200
    assert "event: done" in stream.text
    assert client.post(f"/v1/chats/{chat_id}/stop", headers=headers).json()["status"] == "stopped"
    renamed = client.patch(f"/v1/chats/{chat_id}", headers=headers, json={"title": "Renamed acceptance chat"})
    assert renamed.status_code == 200
    assert renamed.json()["chat"]["title"] == "Renamed acceptance chat"
    assert client.post(f"/v1/chats/{chat_id}/retry", headers=headers).status_code == 200
    assert client.post(f"/v1/chats/{chat_id}/branch", headers=headers).status_code == 200
    assert client.post(f"/v1/chats/{chat_id}/attachments", headers=headers, json={"name": "notes.md", "content": "sample"}).status_code == 200
    archived = client.post(f"/v1/chats/{chat_id}/archive", headers=headers)
    assert archived.status_code == 200

    plan = client.post("/v1/plans", headers=headers, json={"request": "Research local model setup and produce a receipt"})
    assert plan.status_code == 200
    plan_id = plan.json()["plan"]["plan_id"]
    assert plan.json()["plan"]["status"] == "draft"
    assert client.patch(f"/v1/plans/{plan_id}", headers=headers, json={"status": "review"}).status_code == 200
    approved = client.post(f"/v1/plans/{plan_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["receipt"]["payload"]["authority"] == "none"

    workflow = client.post("/v1/workflows", headers=headers, json={"plan_id": plan_id})
    assert workflow.status_code == 200
    workflow_id = workflow.json()["workflow"]["workflow_id"]
    run = client.post(f"/v1/workflows/{workflow_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["workflow"]["status"] == "completed"
    assert run.json()["workflow"]["artifacts"]

    research = client.post("/v1/research", headers=headers, json={"query": "local-first governed AI"})
    assert research.status_code == 200
    assert research.json()["research"]["sources"][0]["claim_boundary"]

    document = client.post("/v1/documents", headers=headers, json={"name": "demo.md", "content": "Hydrogenuine cites local documents.\nReceipts stay local."})
    assert document.status_code == 200
    doc_id = document.json()["document"]["document_id"]
    hits = client.get("/v1/documents/query", headers=headers, params={"q": "receipts"})
    assert hits.status_code == 200
    assert hits.json()["hits"][0]["document_id"] == doc_id

    memory = client.post("/v1/memory", headers=headers, json={"text": "The user prefers local models."})
    assert memory.status_code == 200
    memory_id = memory.json()["memory"]["memory_id"]
    accepted = client.patch(f"/v1/memory/{memory_id}", headers=headers, json={"status": "accepted"})
    assert accepted.status_code == 200
    assert accepted.json()["memory"]["authority"] == "none"

    denied = client.post("/v1/tools/simulated.echo/run", headers=headers, json={"input": "hello"})
    assert denied.status_code == 403
    assert denied.json()["receipt"]["decision"] == "denied"
    lease = client.post("/v1/leases", headers=headers, json={"capability": "simulated.echo", "scope": {"chat_id": chat_id}})
    assert lease.status_code == 200
    lease_id = lease.json()["lease"]["lease_id"]
    assert client.post(f"/v1/leases/{lease_id}/approve", headers=headers).status_code == 200
    allowed = client.post("/v1/tools/simulated.echo/run", headers=headers, json={"input": "hello"})
    assert allowed.status_code == 200
    assert allowed.json()["result"]["verified"] is True
    assert client.post(f"/v1/leases/{lease_id}/revoke", headers=headers).status_code == 200

    exported = client.get("/v1/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["format"] == "hydrogenuine-community-export-v1"
    receipts = client.get("/v1/receipts", headers=headers)
    assert receipts.status_code == 200
    assert len(receipts.json()["receipts"]) >= 8

    disposable = client.post("/v1/chats", headers=headers, json={"title": "Disposable"})
    delete_status = client.delete(f"/v1/chats/{disposable.json()['chat_id']}", headers=headers)
    assert delete_status.status_code == 204
