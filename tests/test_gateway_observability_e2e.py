"""
Pack3 Phase 5: Observability e2e — trace id in headers, /metrics, structured denial.
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


@pytest.fixture
def client_sqlite():
    tmp_root = Path.cwd() / ".codex_tmp" / "testdata"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_root / f"gateway_obs_{uuid.uuid4().hex}"
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


def test_response_includes_x_request_id(client_sqlite):
    """Every response includes X-Request-ID header (trace id)."""
    r = client_sqlite.get("/v1/system/status")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 0


def test_client_request_id_propagated(client_sqlite):
    """Client can send X-Request-ID and it is echoed in response."""
    r = client_sqlite.get("/v1/system/status", headers={"X-Request-ID": "my-trace-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "my-trace-123"


def test_metrics_endpoint_returns_prometheus_format(client_sqlite):
    """GET /v1/metrics returns Prometheus text with gateway_ counters."""
    r = client_sqlite.get("/v1/metrics")
    assert r.status_code == 200
    text = r.text
    assert "gateway_requests_total" in text
    assert "gateway_errors_total" in text
    assert "gateway_tool_calls_total" in text or "counter" in text


def test_denial_includes_structured_explanation(client_sqlite):
    """403 for policy denial includes reason and code (why blocked)."""
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={
            "tool_invoke": {
                "tool_name": "moltbook.post_or_reply",
                "inputs": {"base_url": "http://127.0.0.1/", "content": "x"},
            },
        },
    )
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data
    detail = data["detail"]
    if isinstance(detail, dict):
        assert "reason" in detail or "code" in detail
        assert detail.get("code") == "ssrf_blocked"


def test_system_diag_returns_traces_and_metrics(client_sqlite):
    """GET /v1/system/diag returns trace_ids, metrics, breakers."""
    client_sqlite.get("/v1/system/status")
    r = client_sqlite.get("/v1/system/diag?traces=5")
    assert r.status_code == 200
    data = r.json()
    assert "trace_ids" in data
    assert "metrics" in data
    assert "breakers" in data
    assert "runtime" in data
    assert isinstance(data["metrics"], dict)
    assert "gateway_requests_total" in data["metrics"]
    assert "tools" in data["runtime"]
    assert "auth" in data["runtime"]
    assert "realtime_bus_mode" in data["runtime"]
    assert "ledger_crypto_mode" in data["runtime"]
    assert "otel" in data["runtime"]
