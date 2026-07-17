from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def learning_workspace(tmp_path, monkeypatch):
    proofs = tmp_path / "docs" / "proofs" / "out" / "20260610_shadow_test"
    proofs.mkdir(parents=True)
    summary = {
        "label": "shadow_test",
        "started_at": "2026-06-10T12:00:00Z",
        "ended_at": "2026-06-10T12:00:01Z",
        "checks_passed": True,
        "swarm_run_id": "sw1",
        "syndrome_count": 2,
        "correction_count": 1,
    }
    (proofs / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (proofs / "checks.json").write_text(json.dumps([{"name": "ok", "pass": True}]), encoding="utf-8")
    (proofs / "ENVIRONMENT.json").write_text(json.dumps({"git_commit_hash": "test"}), encoding="utf-8")
    (proofs / "VERSIONS.txt").write_text("test=1\n", encoding="utf-8")
    (proofs / "artifacts.json").write_text(
        json.dumps({"verification_graph": {"node_ids": ["a", "b", "c", "d", "e"]}}),
        encoding="utf-8",
    )
    index = {
        "latest": {"shadow_test": str(proofs)},
        "runs": [{"label": "shadow_test", "folder": str(proofs), "started_at": summary["started_at"], "checks_passed": True}],
    }
    (tmp_path / "docs" / "proofs" / "index.json").write_text(json.dumps(index), encoding="utf-8")
    db = tmp_path / "memory" / "learning" / "corpus.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    return tmp_path


def test_shadow_run_and_activity(operator_client, learning_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/learning/sync", headers=headers)
    shadow = operator_client.post("/api/v1/learning/shadow/run", headers=headers)
    assert shadow.status_code == 200
    body = shadow.json()
    assert body["ok"] is True
    assert body["ledger_count"] >= 0
    activity = operator_client.get("/api/v1/learning/activity", headers=headers)
    assert activity.status_code == 200
    act = activity.json()
    assert act["ok"] is True
    assert len(act["paths"]) == 5
    assert "path_activation" in act
    assert "live_priors" in act
    ledger = operator_client.get("/api/v1/learning/shadow/ledger", headers=headers)
    assert ledger.status_code == 200


def test_live_priors_and_control_group_api(operator_client, learning_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    priors = operator_client.get("/api/v1/learning/live/priors", headers=headers)
    assert priors.status_code == 200
    assert priors.json()["ok"] is True
    cg = operator_client.get("/api/v1/learning/control-group/stats", headers=headers)
    assert cg.status_code == 200
    assert cg.json()["ok"] is True
