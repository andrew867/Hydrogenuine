from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def _write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def test_artifact_registry_api_inventory_and_versions(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write(workspace / "memory/overseer/decision_log.jsonl", "{\"event\":1}\n")
    _write(workspace / "docs/ux/screenshots/home.png", b"png")
    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    monkeypatch.setenv("HG_WORKSPACE", str(workspace))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        sync_resp = client.post("/api/v1/artifact-registry/registry/sync", json={"root": str(workspace)})
        assert sync_resp.status_code == 200
        payload = sync_resp.json()
        assert payload["sync"]["artifacts"] == 2
        assert payload["summary"]["total_artifacts"] == 2

        overview = client.get("/api/v1/artifact-registry/registry")
        assert overview.status_code == 200
        records = overview.json()["artifacts"]
        assert len(records) == 2

        screenshot = next(row for row in records if row["class_key"] == "screenshot")
        detail = client.get(f"/api/v1/artifact-registry/registry/{screenshot['artifact_id']}")
        assert detail.status_code == 200
        assert detail.json()["artifact"]["file_path"].endswith("home.png")

        versions = client.get(f"/api/v1/artifact-registry/registry/{screenshot['artifact_id']}/versions")
        assert versions.status_code == 200
        assert len(versions.json()["versions"]) == 1
    finally:
        app.dependency_overrides.pop(require_api_key, None)
