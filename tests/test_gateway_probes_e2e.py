"""
Pack2-05: Situational testbed e2e. Real probes, real DB, no mocks.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key
from hg_gateway.db import get_connection, _get_db_path


@pytest.fixture
def client_sqlite(tmp_path):
    """Client with SQLite store and probe tables in same DB."""
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


def test_probes_run_light(client_sqlite):
    """POST /v1/system/probes/run with suite light returns run_id and summary; results stored in DB."""
    r = client_sqlite.post("/v1/system/probes/run", json={"suite": "light"})
    assert r.status_code == 200
    data = r.json()
    assert "run_id" in data
    assert data["suite"] == "light"
    assert "summary" in data
    assert "pass" in data["summary"]
    assert "fail" in data["summary"]
    run_id = data["run_id"]
    with get_connection(_get_db_path()) as conn:
        row = conn.execute("SELECT run_id, suite FROM probe_runs WHERE run_id = ?", (run_id,)).fetchone()
        assert row is not None
        assert row["suite"] == "light"
        count = conn.execute("SELECT COUNT(*) AS n FROM probe_results WHERE run_id = ?", (run_id,)).fetchone()["n"]
        assert count >= 2


def test_probes_run_full(client_sqlite):
    """POST /v1/system/probes/run with suite full runs all 5 probe types; results stored."""
    r = client_sqlite.post("/v1/system/probes/run", json={"suite": "full"})
    assert r.status_code == 200
    data = r.json()
    assert data["suite"] == "full"
    run_id = data["run_id"]
    r2 = client_sqlite.get(f"/v1/system/probes/runs/{run_id}")
    assert r2.status_code == 200
    run = r2.json()
    assert run["run_id"] == run_id
    assert "probe_results" in run
    types = {p["probe_type"] for p in run["probe_results"]}
    assert "approval_bypass" in types
    assert "rate_limit" in types
    assert "prompt_injection" in types
    assert "unsafe_tool" in types
    assert "pii_leakage" in types


def test_probes_list_runs(client_sqlite):
    """GET /v1/system/probes/runs returns runs from DB."""
    client_sqlite.post("/v1/system/probes/run", json={"suite": "light"})
    r = client_sqlite.get("/v1/system/probes/runs")
    assert r.status_code == 200
    assert "runs" in r.json()
    assert len(r.json()["runs"]) >= 1


def test_probes_get_run_not_found(client_sqlite):
    """GET /v1/system/probes/runs/{id} for missing run returns 404."""
    r = client_sqlite.get("/v1/system/probes/runs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_probes_run_invalid_suite(client_sqlite):
    """POST /v1/system/probes/run with invalid suite returns 400."""
    r = client_sqlite.post("/v1/system/probes/run", json={"suite": "invalid"})
    assert r.status_code == 400


def test_light_probes_outcomes_real(client_sqlite):
    """Light suite: approval_bypass and rate_limit produce real pass/fail (no stubs)."""
    r = client_sqlite.post("/v1/system/probes/run", json={"suite": "light"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client_sqlite.get(f"/v1/system/probes/runs/{run_id}")
    results = {p["probe_type"]: p for p in r2.json()["probe_results"]}
    assert results["approval_bypass"]["outcome"] == "pass"
    assert results["rate_limit"]["outcome"] == "pass"
