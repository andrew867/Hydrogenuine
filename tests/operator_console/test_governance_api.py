import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    TestClient = None
    app = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    return TestClient(app)


def test_governance_api_end_to_end(client):
    policy = client.post(
        "/api/v1/governance/policies/versions",
        headers=_headers(),
        json={
            "policy_key": "approval_policy",
            "title": "Approval Policy",
            "category": "approval",
            "description": "Test policy",
            "content": {"required_flags": ["human_review"]},
            "rationale": "Test",
            "change_summary": "Initial",
        },
    )
    assert policy.status_code == 200, policy.text
    version_id = policy.json()["version_id"]

    simulate = client.post(
        f"/api/v1/governance/policies/versions/{version_id}/simulate",
        headers=_headers(),
        json={"version_id": version_id, "scenario_label": "operator", "inputs": {"human_review": True}},
    )
    assert simulate.status_code == 200, simulate.text

    activate = client.post(f"/api/v1/governance/policies/versions/{version_id}/activate?actor_id=operator", headers=_headers())
    assert activate.status_code == 200, activate.text

    root = client.post(
        "/api/v1/governance/constitutional-roots",
        headers=_headers(),
        json={
            "workflow_family": "social",
            "title": "Social root",
            "root_goal": "Post with judgment",
            "material_constraints": ["No spam"],
            "approved_subgoals": ["Build rapport"],
            "policy_version_id": version_id,
        },
    )
    assert root.status_code == 200, root.text
    root_id = root.json()["root_id"]

    checkpoint = client.post(
        f"/api/v1/governance/constitutional-roots/{root_id}/checkpoints",
        headers=_headers(),
        json={"summary": "Stable", "state": {"mood": "steady"}, "alignment_score": 0.8},
    )
    assert checkpoint.status_code == 200, checkpoint.text

    drift = client.post(
        f"/api/v1/governance/constitutional-roots/{root_id}/drift",
        headers=_headers(),
        json={"severity": "watch", "summary": "Too sharp", "details": {"bucket": "tone"}},
    )
    assert drift.status_code == 200, drift.text

    drift_review = client.get(f"/api/v1/governance/drift?workflow_family=social&root_id={root_id}&limit=5", headers=_headers())
    assert drift_review.status_code == 200, drift_review.text
    review_payload = drift_review.json()["drift_review"]
    assert review_payload["status"] in {"watch", "blocked", "healthy"}
    assert review_payload["root"]["root_id"] == root_id
    assert review_payload["recent_drift_events"]
    assert review_payload["recent_drift_events"][0]["title"] == "Drift detected"

    bench = client.post(
        "/api/v1/governance/gate/benchmark-sets",
        headers=_headers(),
        json={"workflow_family": "social", "title": "Social gate", "description": "Test", "weights": {"p_h": 0.3, "p_ai": 0.2, "p_h_odei": 0.5}},
    )
    assert bench.status_code == 200, bench.text
    benchmark_set_id = bench.json()["benchmark_set_id"]

    bench_run = client.post(
        "/api/v1/governance/gate/benchmark-runs",
        headers=_headers(),
        json={"benchmark_set_id": benchmark_set_id, "workflow_family": "social", "candidate_label": "v1", "observations": {"p_h": 0.7, "p_ai": 0.5, "p_h_odei": 0.8}},
    )
    assert bench_run.status_code == 200, bench_run.text
    benchmark_run_id = bench_run.json()["benchmark_run_id"]

    evaluation = client.post(
        "/api/v1/governance/gate/evaluate",
        headers=_headers(),
        json={"benchmark_run_id": benchmark_run_id, "policy_version_id": version_id},
    )
    assert evaluation.status_code == 200, evaluation.text
    evaluation_id = evaluation.json()["evaluation_id"]

    release = client.post(
        "/api/v1/governance/gate/release-verdicts",
        headers=_headers(),
        json={"workflow_family": "social", "target_kind": "workflow", "target_id": "social", "evaluation_id": evaluation_id, "verdict": "eligible", "reason": "ready"},
    )
    assert release.status_code == 200, release.text

    dashboard = client.get("/api/v1/governance/dashboard", headers=_headers())
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["counts"]["receipts"] >= 1
    assert "continuity_quality" in dashboard.json()
    assert dashboard.json()["continuity_quality"]["status"] in {"missing", "healthy", "watch", "blocked"}

    receipts = client.get("/api/v1/governance/receipts", headers=_headers())
    assert receipts.status_code == 200, receipts.text
    receipt_id = receipts.json()["receipts"][0]["receipt_id"]
    verify = client.post(f"/api/v1/governance/receipts/{receipt_id}/verify", headers=_headers())
    assert verify.status_code == 200, verify.text
