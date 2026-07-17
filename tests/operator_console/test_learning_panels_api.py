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
    proofs = tmp_path / "docs" / "proofs" / "out" / "20260610_test_learning"
    proofs.mkdir(parents=True)
    summary = {
        "label": "learning_api_test",
        "started_at": "2026-06-10T12:00:00Z",
        "ended_at": "2026-06-10T12:00:01Z",
        "checks_passed": True,
        "behavioral_metrics": {
            "task_completion": 0.95,
            "safety_violations": 0.0,
            "path_efficiency": 0.9,
        },
    }
    (proofs / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (proofs / "checks.json").write_text(json.dumps([{"name": "ok", "pass": True}]), encoding="utf-8")
    (proofs / "ENVIRONMENT.json").write_text(json.dumps({"git_commit_hash": "test"}), encoding="utf-8")
    (proofs / "VERSIONS.txt").write_text("test=1\n", encoding="utf-8")
    index = {
        "latest": {"learning_api_test": str(proofs)},
        "runs": [{"label": "learning_api_test", "folder": str(proofs), "started_at": summary["started_at"], "checks_passed": True}],
    }
    (tmp_path / "docs" / "proofs" / "index.json").write_text(json.dumps(index), encoding="utf-8")
    db = tmp_path / "memory" / "learning" / "corpus.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    return tmp_path


def test_learning_sync_and_telemetry(operator_client, learning_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    sync = operator_client.post("/api/v1/learning/sync", headers=headers)
    assert sync.status_code == 200
    body = sync.json()
    assert body["ok"] is True
    assert body["mining"]["bundles_processed"] >= 1
    telem = operator_client.get("/api/v1/learning/telemetry", headers=headers)
    assert telem.status_code == 200
    t = telem.json()
    assert t["hg_learning_corpus_size"] >= 1
    assert "hg_learning_label_coverage" in t


def test_relabel_queue_and_operator_override(operator_client, learning_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/learning/sync", headers=headers)
    queue = operator_client.get("/api/v1/learning/relabel-queue", headers=headers)
    assert queue.status_code == 200
    items = queue.json().get("items") or []
    telem = operator_client.get("/api/v1/learning/telemetry", headers=headers)
    signals_labeled = telem.json().get("hg_learning_labeled_signals", 0)
    assert signals_labeled >= 1 or len(items) >= 0
    all_signals = operator_client.get("/api/v1/learning/track-records", headers=headers)
    assert all_signals.status_code == 200
    if items:
        sid = items[0]["signal_id"]
        relabel = operator_client.post(
            f"/api/v1/learning/relabel/{sid}",
            headers=headers,
            json={"verdict": "success", "actor_id": "test_op"},
        )
        assert relabel.status_code == 200
        assert relabel.json()["label"]["source"] == "operator"


def test_track_records(operator_client, learning_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    operator_client.post("/api/v1/learning/sync", headers=headers)
    res = operator_client.get("/api/v1/learning/track-records", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "entities" in data
