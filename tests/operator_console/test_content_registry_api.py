from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_content_registry_inventory_and_edit_round_trip(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    _write(workspace / "skills/automation/tasks/example-task.md", "# Example Task\nTask body.\n")
    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    monkeypatch.setenv("HG_WORKSPACE", str(workspace))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        sync_resp = client.post("/api/v1/content/registry/sync", json={"root": str(workspace)})
        assert sync_resp.status_code == 200
        payload = sync_resp.json()
        assert payload["summary"]["total_documents"] == 1
        assert payload["summary"]["by_class"][0]["class_key"] == "task"

        overview = client.get("/api/v1/content/registry")
        assert overview.status_code == 200
        docs = overview.json()["documents"]
        assert len(docs) == 1
        content_id = docs[0]["content_id"]

        doc = client.get(f"/api/v1/content/registry/{content_id}")
        assert doc.status_code == 200
        doc_payload = doc.json()["document"]
        assert doc_payload["title"] == "Example Task"
        assert doc_payload["versions"][0]["state"] == "imported"

        save = client.put(
            f"/api/v1/content/registry/{content_id}",
            json={
                "content_markdown": "# Example Task\nTask body updated.\n",
                "title": "Example Task",
                "actor_id": "operator_console",
                "change_summary": "refined body copy",
            },
        )
        assert save.status_code == 200
        saved = save.json()["document"]
        assert saved["versions"][0]["version_number"] == 2
        assert saved["versions"][0]["state"] == "published"

        archive = client.post(
            f"/api/v1/content/registry/{content_id}/archive",
            json={"actor_id": "operator_console", "change_summary": "archive for review"},
        )
        assert archive.status_code == 200
        archived = archive.json()["document"]
        assert archived["archived"] is True
        assert archived["latest_status"] == "archived"

        restore = client.post(
            f"/api/v1/content/registry/{content_id}/restore",
            json={"actor_id": "operator_console", "change_summary": "restore to active"},
        )
        assert restore.status_code == 200
        restored = restore.json()["document"]
        assert restored["archived"] is False
        assert restored["latest_status"] == "current"
        assert len(restored["versions"]) == 4
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_content_registry_create_endpoint(monkeypatch, tmp_path: Path):
    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/content/registry",
            json={
                "class_key": "runbook",
                "file_path": "docs/runbooks/OPERATOR_TEST.md",
                "title": "Operator Test Runbook",
                "content_markdown": "# Operator Test Runbook\n\nThis is a runbook.",
                "actor_id": "operator_console",
                "change_summary": "created from api test",
            },
        )
        assert response.status_code == 200
        payload = response.json()["document"]
        assert payload["class_key"] == "runbook"
        assert payload["versions"][0]["version_number"] == 1
        assert payload["versions"][0]["state"] == "published"
    finally:
        app.dependency_overrides.pop(require_api_key, None)
