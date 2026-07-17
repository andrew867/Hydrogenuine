"""
Schedule API: POST/GET/PATCH /v1/schedule/jobs, run_once, run_requests.
Uses temp SQLite DB so migrations create scheduled_jobs and schedule_run_requests. Tenant-scoped and audited.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from hg_core.tenancy.context import TenantContext
from hg_gateway.main import app
from hg_gateway.auth import verify_api_key, get_tenant_context


@pytest.fixture
def temp_db():
    """Use a temp SQLite path so gateway DB has schedule tables (migration v16)."""
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    try:
        prev = os.environ.get("HG_GATEWAY_DB_PATH")
        os.environ["HG_GATEWAY_DB_PATH"] = path
        yield path
    finally:
        if prev is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
        try:
            os.unlink(path)
        except Exception:
            pass


@pytest.fixture
def client(temp_db):
    """TestClient with auth and tenant overrides; DB path set so schedule routes use real SQLite."""
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(tenant_id="default", environment="dev")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)


def test_schedule_create_list(client):
    """POST create job, GET list returns it."""
    r = client.post("/v1/schedule/jobs", json={"job_id": "test-job-1", "cron": "0 * * * *"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("job_id") == "test-job-1"
    assert data.get("cron") == "0 * * * *"

    r2 = client.get("/v1/schedule/jobs")
    assert r2.status_code == 200
    jobs = r2.json().get("jobs", [])
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "test-job-1"
    assert jobs[0]["cron"] == "0 * * * *"
    assert jobs[0]["status"] == "active"


def test_schedule_create_interval(client):
    """Create job with interval_minutes."""
    r = client.post("/v1/schedule/jobs", json={"job_id": "interval-job", "interval_minutes": 15})
    assert r.status_code == 200
    assert r.json().get("interval_minutes") == 15
    r2 = client.get("/v1/schedule/jobs")
    assert any(j["job_id"] == "interval-job" for j in r2.json()["jobs"])


def test_schedule_create_validation(client):
    """Missing job_id or both cron/interval returns 400."""
    r = client.post("/v1/schedule/jobs", json={"cron": "0 * * * *"})
    assert r.status_code == 400
    r = client.post("/v1/schedule/jobs", json={"job_id": "x", "cron": "0 * * * *", "interval_minutes": 10})
    assert r.status_code == 400


def test_schedule_create_duplicate(client):
    """Duplicate job_id for same tenant returns 409."""
    client.post("/v1/schedule/jobs", json={"job_id": "dup", "cron": "0 * * * *"})
    r = client.post("/v1/schedule/jobs", json={"job_id": "dup", "cron": "5 * * * *"})
    assert r.status_code == 409


def test_schedule_patch(client):
    """PATCH updates job and list reflects it."""
    client.post("/v1/schedule/jobs", json={"job_id": "patch-job", "cron": "0 * * * *"})
    r = client.patch("/v1/schedule/jobs/patch-job", json={"status": "paused"})
    assert r.status_code == 200
    r2 = client.get("/v1/schedule/jobs")
    job = next(j for j in r2.json()["jobs"] if j["job_id"] == "patch-job")
    assert job["status"] == "paused"


def test_schedule_patch_not_found(client):
    """PATCH non-existent job returns 404."""
    r = client.patch("/v1/schedule/jobs/nonexistent", json={"status": "active"})
    assert r.status_code == 404


def test_schedule_run_once(client):
    """run_once creates pending run request and returns request_id."""
    client.post("/v1/schedule/jobs", json={"job_id": "run-me", "interval_minutes": 60})
    r = client.post("/v1/schedule/jobs/run-me/run_once")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "request_id" in data
    assert data.get("status") == "pending"

    r2 = client.get("/v1/schedule/run_requests", params={"status": "pending"})
    assert r2.status_code == 200
    reqs = r2.json().get("run_requests", [])
    assert len(reqs) >= 1
    assert any(req["job_id"] == "run-me" and req["status"] == "pending" for req in reqs)


def test_schedule_run_once_not_found(client):
    """run_once on non-existent job returns 404."""
    r = client.post("/v1/schedule/jobs/missing/run_once")
    assert r.status_code == 404
