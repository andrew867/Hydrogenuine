import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from hg_core.tenancy.context import TenantContext
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", path)
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_ENV", "test")
    monkeypatch.setenv("HG_RELEASE_GATE_ENFORCED", "1")
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(tenant_id="default", environment="test")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)
        try:
            os.unlink(path)
        except OSError:
            pass


def test_run_once_dedupes_pending_request(client):
    from hg_core.gate import create_benchmark_set, create_release_verdict, evaluate_benchmark_run, record_benchmark_run

    client.post("/v1/schedule/jobs", json={"job_id": "social", "interval_minutes": 15})
    bench = create_benchmark_set(workflow_family="social", title="Gate", description="Test", weights={"p_h": 0.3, "p_ai": 0.2, "p_h_odei": 0.5})
    run = record_benchmark_run(benchmark_set_id=bench["benchmark_set_id"], workflow_family="social", candidate_label="v1", observations={"p_h": 0.8, "p_ai": 0.2, "p_h_odei": 0.9})
    evaluation = evaluate_benchmark_run(benchmark_run_id=run["benchmark_run_id"])
    create_release_verdict(workflow_family="social", target_kind="workflow", target_id="social", evaluation_id=evaluation["evaluation_id"], verdict="eligible")

    first = client.post("/v1/schedule/jobs/social/run_once")
    second = client.post("/v1/schedule/jobs/social/run_once")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["request_id"] == second.json()["request_id"]
    assert second.json()["deduped"] is True
