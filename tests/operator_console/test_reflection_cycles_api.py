from __future__ import annotations

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def test_reflection_cycles_api_status_and_run(monkeypatch, tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HG_WORKSPACE", str(workspace))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(workspace / "memory" / "gateway.sqlite3"))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        status_resp = client.get("/api/v1/reflections/cycles")
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["ok"] is True
        assert len(status["cycles"]) >= 3

        run_resp = client.post("/api/v1/reflections/cycles/run", json={"force": True})
        assert run_resp.status_code == 200
        run_payload = run_resp.json()
        assert run_payload["ok"] is True
        assert len(run_payload["cycles"]) >= 3
        assert "summary" in run_payload
    finally:
        app.dependency_overrides.pop(require_api_key, None)
