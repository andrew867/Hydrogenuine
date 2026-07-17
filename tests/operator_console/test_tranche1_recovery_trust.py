from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app as gateway_app
from operator_console.server.app.main import app as operator_app


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


def test_demo_login_enabled_in_demo_env(gateway_client, monkeypatch):
    monkeypatch.setenv("HG_OIDC_ENABLED", "0")
    monkeypatch.setenv("HG_ENV", "Demo")
    monkeypatch.delenv("HG_DEMO_LOGIN_ENABLED", raising=False)
    cfg = gateway_client.get("/v1/auth/config")
    assert cfg.status_code == 200
    assert cfg.json().get("demo_login_enabled") is True
    login = gateway_client.post("/v1/auth/demo/login")
    assert login.status_code == 200
    body = login.json()
    assert "operator" in body.get("roles", [])
    assert body.get("login_mode") == "demo_deterministic"


def test_trust_metrics_endpoint(operator_client, tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    run_dir = tmp_path / "docs" / "proofs" / "out" / "20260324_120000_investor_demo"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"checks_passed": True, "started_at": now, "ended_at": now, "provenance_available": True}),
        encoding="utf-8",
    )
    index = {"latest": {"investor_demo": str(run_dir)}, "runs": []}
    (tmp_path / "docs" / "proofs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "proofs" / "index.json").write_text(json.dumps(index), encoding="utf-8")
    res = operator_client.get("/api/v1/proofs/trust-metrics", headers={"Authorization": "Bearer test-api-key"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "metrics" in data
    assert data["metrics"]["browser_summary"]["evidence_links"]["recovery"] == "#/recovery"


def test_recovery_summary(operator_client):
    res = operator_client.get("/api/v1/recovery/summary", headers={"Authorization": "Bearer test-api-key"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "counts" in data
    assert data["evidence_links"]["timeline"] == "#/timeline"


def test_admin_proofs_recovery_link(gateway_client, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_ADMIN_KEY", "admin-test")
    res = gateway_client.get("/v1/admin/proofs/index", headers={"X-Admin-Key": "admin-test"})
    assert res.status_code == 200
    metrics = res.json().get("metrics") or {}
    assert metrics.get("browser_summary", {}).get("evidence_links", {}).get("recovery") == "#/recovery"
