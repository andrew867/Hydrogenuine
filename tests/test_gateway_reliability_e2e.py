"""
Pack3 Phase 4: Reliability e2e — system status exposes breakers; circuit open returns 503.
"""

import os
import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key
from hg_core.runtime.reliability import (
    get_all_breaker_states,
    record_breaker_failure,
    record_breaker_success,
)


@pytest.fixture
def client_sqlite():
    tmp_root = Path.cwd() / ".codex_tmp" / "testdata"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_root / f"gateway_rel_{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_system_status_returns_diagnostics(client_sqlite):
    """GET /v1/system/status returns status and diagnostics."""
    r = client_sqlite.get("/v1/system/status")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in ("green", "yellow", "red")
    assert "diagnostics" in data
    diag = {d.get("component"): d for d in data.get("diagnostics", [])}
    assert "tools" in diag
    assert "realtime_bus" in diag
    assert "ledger_crypto" in diag
    assert "auth" in diag
    assert "store" in diag
    assert diag["store"].get("backend") == "sqlite"
    assert diag["store"].get("canonical_store") == "sqlite"
    assert diag["store"].get("db_path_is_workspace_memory") is False


def test_system_status_includes_breakers_after_tool_run(client_sqlite):
    """After a tool run, system status diagnostics can include circuit_breakers."""
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={"tool_invoke": {"tool_name": "gateway.echo", "inputs": {"message": "hi"}}},
    )
    r = client_sqlite.get("/v1/system/status")
    assert r.status_code == 200
    data = r.json()
    diag = {d.get("component"): d for d in data.get("diagnostics", [])}
    assert "circuit_breakers" in diag
    breakers = diag["circuit_breakers"].get("breakers") or []
    keys = [b.get("key") for b in breakers]
    assert any(k == "tool:gateway.echo" for k in keys)


def test_circuit_open_returns_503(client_sqlite):
    """When breaker is open for a tool, invoking that tool returns 503."""
    # Force breaker open for gateway.echo (threshold=1)
    record_breaker_failure("tool:gateway.echo", failure_threshold=1, recovery_timeout_s=60)
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={"tool_invoke": {"tool_name": "gateway.echo", "inputs": {"message": "x"}}},
    )
    assert r.status_code == 503
    record_breaker_success("tool:gateway.echo")
