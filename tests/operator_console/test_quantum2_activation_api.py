from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def q2_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    return tmp_path


def test_activation_state_and_shadow_enable(operator_client, q2_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    state = operator_client.get("/api/v1/quantum2/activation/state", headers=headers)
    assert state.status_code == 200
    body = state.json()
    assert body["ok"] is True
    assert len(body["modules"]) == 5
    enable = operator_client.post(
        "/api/v1/quantum2/activation/modules/fingerprint_codec/enable-shadow",
        headers=headers,
        json={"actor_id": "operator", "rationale": "shadow trial"},
    )
    assert enable.status_code == 200
    assert enable.json()["mode"] == "shadow"
    history = operator_client.get("/api/v1/quantum2/activation/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["entries"]) >= 1


def test_promote_live_requires_sign_off(operator_client, q2_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    blocked = operator_client.post(
        "/api/v1/quantum2/activation/modules/fingerprint_codec/promote-live",
        headers=headers,
        json={"sign_off": False},
    )
    assert blocked.status_code == 400
    ok = operator_client.post(
        "/api/v1/quantum2/activation/modules/fingerprint_codec/promote-live",
        headers=headers,
        json={"sign_off": True, "rationale": "P-E1 eligible"},
    )
    assert ok.status_code == 200
    assert ok.json()["mode"] == "live"


def test_run_shadow_workloads_and_go_no_go(operator_client, q2_workspace, monkeypatch):
    monkeypatch.setenv("Q2_PRODUCTION_SHADOW_BATCH_COUNT", "2")
    headers = {"Authorization": "Bearer test-api-key"}
    run = operator_client.post("/api/v1/quantum2/activation/run-shadow-workloads", headers=headers)
    assert run.status_code == 200
    body = run.json()
    assert body["ok"] is True
    assert len(body["batch"]["runs"]) >= 2
    go = operator_client.get("/api/v1/quantum2/activation/go-no-go", headers=headers)
    assert go.status_code == 200
    assert go.json()["ok"] is True


def test_flip_shadow_first_live_and_summary(operator_client, q2_workspace, monkeypatch):
    monkeypatch.setenv("Q2_PRODUCTION_SHADOW_BATCH_COUNT", "2")
    headers = {"Authorization": "Bearer test-api-key"}
    run = operator_client.post("/api/v1/quantum2/activation/run-shadow-workloads", headers=headers)
    assert run.status_code == 200
    flip = operator_client.post(
        "/api/v1/quantum2/activation/flip-shadow-first-live",
        headers=headers,
        json={"actor_id": "operator", "rationale": "go-no-go green"},
    )
    assert flip.status_code == 200
    body = flip.json()
    assert body["ok"] is True
    assert len(body.get("verifications") or []) == 3
    summary = operator_client.get("/api/v1/quantum2/activation/live-summary", headers=headers)
    assert summary.status_code == 200
    live = summary.json()
    assert live["live_count"] >= 3
    for comp in ("shell_model", "barbell_topology", "sum_rule_engine"):
        assert comp in live["live_modules"]


def test_divergence_review(operator_client, q2_workspace):
    from hg_quantum.shadow_telemetry import record_shadow_event

    record_shadow_event("sum_rule_engine", "allocation_compare", {"diverged": True}, workspace_root=q2_workspace)
    headers = {"Authorization": "Bearer test-api-key"}
    review = operator_client.get("/api/v1/quantum2/activation/divergence/sum_rule_engine", headers=headers)
    assert review.status_code == 200
    data = review.json()
    assert data["shadow"]["total_events"] >= 1
