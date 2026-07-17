from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def test_task_registry_api_inventory_and_versions(monkeypatch, tmp_path: Path) -> None:
    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        sync_resp = client.post("/api/v1/task-registry/registry/sync", json={})
        assert sync_resp.status_code == 200
        payload = sync_resp.json()
        assert payload["sync"]["documents"] >= 1
        assert payload["summary"]["total_tools"] >= 1

        overview = client.get("/api/v1/task-registry/registry")
        assert overview.status_code == 200
        records = overview.json()["tasks"]
        assert len(records) >= 1

        task_name = next(row["task_name"] for row in records if row["task_name"] == "moltbook-engage")
        detail = client.get(f"/api/v1/task-registry/registry/{task_name}")
        assert detail.status_code == 200
        assert detail.json()["task"]["session_target"].startswith("automation-")

        versions = client.get(f"/api/v1/task-registry/registry/{task_name}/versions")
        assert versions.status_code == 200
        assert len(versions.json()["versions"]) >= 1

        save_resp = client.put(
            f"/api/v1/task-registry/registry/{task_name}",
            json={"metadata": {"notes": "updated from test"}, "disabled": True, "sandbox_mode": "direct"},
        )
        assert save_resp.status_code == 200
        saved = save_resp.json()["task"]
        assert saved["active"] == 0
        assert saved["latest_status"] == "disabled"
        assert saved["sandbox_mode"] == "direct"

        restore_resp = client.put(
            f"/api/v1/task-registry/registry/{task_name}",
            json={"metadata": {"notes": "updated from test"}, "disabled": False, "archived": False, "sandbox_mode": "sandbox"},
        )
        assert restore_resp.status_code == 200
        restored = restore_resp.json()["task"]
        assert restored["active"] == 1
        assert restored["latest_status"] == "current"
        assert restored["sandbox_mode"] == "sandbox"
    finally:
        app.dependency_overrides.pop(require_api_key, None)
