from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def _write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def test_executable_registry_api_inventory_and_versions(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write(workspace / "hg_platforms/__init__.py", '"""Platform package."""\n')
    _write(workspace / "hg_platforms/base.py", '"""Base types for platforms."""\n')
    _write(workspace / "hg_platforms/registry.py", '"""Platform registry."""\n')
    _write(workspace / "hg_platforms/fourclaw/create_fourclaw_thread.py", '"""Create fourclaw thread."""\n')

    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    monkeypatch.setenv("HG_WORKSPACE", str(workspace))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        sync_resp = client.post("/api/v1/executable-registry/registry/sync", json={"root": str(workspace)})
        assert sync_resp.status_code == 200
        payload = sync_resp.json()
        assert payload["sync"]["documents"] >= 4
        assert payload["summary"]["total_tools"] >= 4

        overview = client.get("/api/v1/executable-registry/registry")
        assert overview.status_code == 200
        records = overview.json()["executables"]
        assert len(records) >= 4

        detail = client.get(f"/api/v1/executable-registry/registry/{records[0]['tool_id']}")
        assert detail.status_code == 200
        assert detail.json()["executable"]["file_path"].endswith(".py")

        versions = client.get(f"/api/v1/executable-registry/registry/{records[0]['tool_id']}/versions")
        assert versions.status_code == 200
        assert len(versions.json()["versions"]) >= 1
    finally:
        app.dependency_overrides.pop(require_api_key, None)
