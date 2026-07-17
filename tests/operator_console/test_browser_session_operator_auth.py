from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

from hg_gateway.session_store import create_session

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    app = None
    TestClient = None


@pytest.fixture
def client(monkeypatch):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    root = Path(".pytest-tmp-browser-auth") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(root / "gateway.sqlite3"))
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_API_KEY", "test-api-key")
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "test-api-key")
    try:
        yield TestClient(app)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_operator_api_accepts_browser_session_cookie(client):
    session_id, _csrf = create_session(
        tenant_id="default",
        principal_id="demo-operator",
        roles=["operator"],
        ttl_seconds=3600,
    )

    response = client.get("/api/v1/config/env", cookies={"hg_session": session_id})

    assert response.status_code == 200
    assert "env" in response.json()
    assert "safe_local_only" in response.json()
