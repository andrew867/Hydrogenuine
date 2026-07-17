"""API tests for Operator Console workflow/fault/retention/operator/SLA endpoints."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    _client_fixture = lambda: TestClient(app)
else:
    app = None
    _client_fixture = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_workflows_list(client):
    """GET /api/v1/workflows returns list of primary workflows."""
    r = client.get("/api/v1/workflows", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "workflows" in data
    assert isinstance(data["workflows"], list)


def test_workflows_detail(client):
    """GET /api/v1/workflows/{id} returns workflow declaration."""
    r = client.get("/api/v1/workflows/fourclaw-auto-post", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "workflow" in data
    assert data["workflow"].get("workflow_id") == "fourclaw-auto-post"


def test_workflows_acceptance_checks(client):
    """POST /api/v1/workflows/{id}/acceptance-checks returns results."""
    r = client.post(
        "/api/v1/workflows/fourclaw-auto-post/acceptance-checks",
        headers=_headers(),
        json={},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "results" in data
    assert isinstance(data["results"], list)


def test_fault_scenarios(client):
    """GET /api/v1/fault/scenarios returns scenarios and by_workflow."""
    r = client.get("/api/v1/fault/scenarios", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "scenarios" in data
    assert "by_workflow" in data


def test_fault_run(client):
    """POST /api/v1/fault/run returns outcome."""
    r = client.post(
        "/api/v1/fault/run",
        headers=_headers(),
        json={"workflow_id": "fourclaw-auto-post", "scenario_id": "transient_network"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "outcome" in data
    assert "failure_class" in data["outcome"] or "terminal" in data["outcome"]


def test_retention_redact_preview(client):
    """POST /api/v1/retention/redact-preview returns redacted payload."""
    r = client.post(
        "/api/v1/retention/redact-preview",
        headers=_headers(),
        json={"api_key": "secret", "data": "ok"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "redacted" in data


def test_operator_status_overview(client):
    """GET /api/v1/operator/status-overview returns overview."""
    r = client.get("/api/v1/operator/status-overview", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "recent" in data or "paused" in data or "breaker_states" in data


def test_operator_incident_queue(client):
    """GET /api/v1/operator/incident-queue returns items list."""
    r = client.get("/api/v1/operator/incident-queue", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "items" in data
    assert isinstance(data["items"], list)


def test_operator_approvals(client):
    """GET /api/v1/operator/approvals returns items list."""
    r = client.get("/api/v1/operator/approvals", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "items" in data
    assert "evidence_timeline" in data


def test_operator_evaluate_approval(client):
    """POST /api/v1/operator/approval/evaluate returns decision."""
    r = client.post(
        "/api/v1/operator/approval/evaluate",
        headers=_headers(),
        json={"workflow_id": "fourclaw-auto-post", "action_summary": {}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "decision" in data
    assert data["decision"] in ("approved", "denied")


def test_sla_daily(client):
    """GET /api/v1/sla/daily returns report."""
    r = client.get("/api/v1/sla/daily", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "report" in data


def test_sla_weekly(client):
    """GET /api/v1/sla/weekly returns report."""
    r = client.get("/api/v1/sla/weekly", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "report" in data
    assert "success_rate" in data["report"] or "per_workflow" in data["report"]


def test_operator_approvals_supports_workflow_filter(client, tmp_path, monkeypatch):
    import hg_gateway.store as store_module

    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "ops-runtime")
    store_module._store = None
    try:
        store = store_module.get_store()
        store.approval_add(
            "ops-runtime",
            kind="tool_invoke",
            title="Approve write",
            summary="runtime queue entry",
            risk="high",
            requested_by="agent-runtime",
            payload={"graph_id": "fourclaw-auto-post", "run_id": "run-123"},
            chat_id="chat-ops",
        )
        r = client.get(
            "/api/v1/operator/approvals?workflow_id=fourclaw-auto-post",
            headers=_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert data.get("total") == 1
        assert data["items"][0]["workflow_id"] == "fourclaw-auto-post"
        assert data["items"][0]["origin"]["run_id"] == "run-123"
        assert data["items"][0]["origin"]["chat_id"] == "chat-ops"
        assert data["items"][0]["status"] == "pending"
    finally:
        store_module._store = None


def test_operator_approvals_enriches_social_write_release_state(client, tmp_path, monkeypatch):
    import hg_gateway.store as store_module
    import app.api.operator_actions as operator_actions
    import app.services.review_handoff_summary as review_handoff_summary

    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "ops-runtime")
    store_module._store = None
    try:
        store = store_module.get_store()
        store.approval_add(
            "ops-runtime",
            kind="social_write",
            title="Approve write",
            summary="runtime queue entry",
            risk="high",
            requested_by="agent-runtime",
            payload={
                "type": "social_write_review",
                "workflow_id": "fourclaw-auto-post",
                "graph_id": "fourclaw-auto-post",
                "entity_approval_id": "approval-entity-1",
            },
        )
        monkeypatch.setattr(
            operator_actions,
            "_enrich_runtime_approval",
            lambda row: {
                **row,
                "entity_approval_id": "approval-entity-1",
                "review_release_state": {
                    "release_ready": False,
                    "release_blockers": ["operational_resume_checkpoint_required"],
                    "required_next_action": "approve_resume",
                    "action_hint": "Approve a fresh operational resume checkpoint before release.",
                },
                "workflow_status_summary": {
                    "workflow_id": "fourclaw-auto-post",
                    "activity_href": "#/activity?workflow_id=fourclaw-auto-post",
                },
            },
        )
        monkeypatch.setattr(review_handoff_summary, "list_runs_index", lambda limit=500: [])
        r = client.get("/api/v1/operator/approvals", headers=_headers())
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert data["items"][0]["entity_approval_id"] == "approval-entity-1"
        assert data["items"][0]["review_release_state"]["required_next_action"] == "approve_resume"
        assert "operational_resume_checkpoint_required" in data["items"][0]["review_release_state"]["release_blockers"]
        assert data["items"][0]["workflow_status_summary"]["workflow_id"] == "fourclaw-auto-post"
        assert data["items"][0]["workflow_status_summary"]["activity_href"] == "#/activity?workflow_id=fourclaw-auto-post"
    finally:
        store_module._store = None
        monkeypatch.delenv("HG_GATEWAY_STORE", raising=False)
        monkeypatch.delenv("HG_GATEWAY_DB_PATH", raising=False)
        monkeypatch.delenv("HG_OPERATOR_TENANT_ID", raising=False)


def test_workflow_dedup_endpoint_returns_entries_and_run_summary(client, tmp_path):
    wf_dir = tmp_path / "memory" / "automation" / "automation-fourclaw-auto-post"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "post_dedupe.json").write_text(
        json.dumps(
            {
                "entries": {
                    "idem-1": {
                        "at": "2026-02-27T12:01:00Z",
                        "tool_name": "fourclaw-auto-post",
                        "outputs": {"thread_id": "t-1"},
                        "usage": {"external_calls": 1},
                        "timeout_s": 300,
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "wf1" / "run_1"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "graph_id": "fourclaw-auto-post",
                "final_status": "completed",
                "started_at": "2026-02-27T12:00:00Z",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with patch("app.api.workflows._workspace_root", return_value=tmp_path):
        r = client.get(
            "/api/v1/workflows/fourclaw-auto-post/dedup",
            headers=_headers(),
        )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data["workflow_id"] == "fourclaw-auto-post"
    assert data["total"] == 1
    assert data["items"][0]["idempotency_key"] == "idem-1"
    assert data["run_summary"]["latest_run_id"] == "run-1"
