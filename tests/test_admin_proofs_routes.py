"""
Admin proof service routes: auth and index. No mocks.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_proofs_index_requires_admin_key(client):
    """GET /v1/admin/proofs/index without or with wrong X-Admin-Key returns 403 (503 if admin key not configured)."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.get("/v1/admin/proofs/index")
        assert r.status_code == 403
        r2 = client.get("/v1/admin/proofs/index", headers={"X-Admin-Key": "wrong"})
        assert r2.status_code == 403
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_admin_proofs_index_with_admin_key(client):
    """GET /v1/admin/proofs/index with valid X-Admin-Key returns 200 and structure."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.get("/v1/admin/proofs/index", headers={"X-Admin-Key": "test-admin-key"})
        assert r.status_code == 200
        data = r.json()
        assert "latest" in data
        assert "runs" in data
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_admin_proofs_index_includes_browser_safe_trust_summary(client, tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    now = datetime.now(timezone.utc).isoformat()
    labels = [
        "investor_demo",
        "drift_quarantine_demo",
        "prompt_injection_hardening_demo",
        "soak_trust_demo",
    ]
    latest = {}
    runs = []
    for label in labels:
        run_dir = workspace / "docs" / "proofs" / "out" / f"20260324_120000_{label}"
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "label": label,
            "started_at": now,
            "ended_at": now,
            "checks_passed": True,
            "provenance_available": True,
            "review_turnaround_seconds": 42,
            "trust_metrics": {
                "continuity_quality": {
                    "status": "healthy",
                    "quality_score": 91,
                }
            },
        }
        if label == "soak_trust_demo":
            summary.update({
                "retry_recovery_ok": True,
                "restart_persistence_ok": True,
                "artifact_cleanup_ok": True,
                "retention_job_ok": True,
            })
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        latest[label] = str(run_dir)
        runs.append(
            {
                "label": label,
                "folder": str(run_dir),
                "started_at": now,
                "checks_passed": True,
            }
        )
    index = {
        "latest": latest,
        "runs": runs,
    }
    docs = workspace / "docs" / "proofs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "index.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.setenv("HG_WORKSPACE", str(workspace))
    monkeypatch.setenv("HG_GATEWAY_ADMIN_KEY", "test-admin-key")
    try:
        r = client.get("/v1/admin/proofs/index", headers={"X-Admin-Key": "test-admin-key"})
        assert r.status_code == 200
        data = r.json()
        metrics = data["metrics"]
        assert metrics["browser_summary"]["status"] == "healthy"
        assert metrics["browser_summary"]["evidence_links"]["timeline"] == "#/timeline"
        assert metrics["browser_summary"]["evidence_links"]["recovery"] == "#/recovery"
        assert metrics["browser_summary"]["evidence_links"]["proofs"] == "#/proofs/run"
        demo = metrics["canonical_demos"][0]
        assert demo["label"] == "investor_demo"
        assert demo["run_id"] == "20260324_120000_investor_demo"
        assert demo["status"] == "healthy"
        assert demo["freshness_state"] in {"fresh", "recent", "unknown"}
        assert demo["provenance_label"] == "available"
        assert demo["evidence_files"]
    finally:
        monkeypatch.delenv("HG_WORKSPACE", raising=False)
        monkeypatch.delenv("HG_GATEWAY_ADMIN_KEY", raising=False)


def test_admin_proofs_run_requires_admin_key(client):
    """POST /v1/admin/proofs/run without or with wrong X-Admin-Key returns 403."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.post("/v1/admin/proofs/run", json={"label": "ticket_triage_5"})
        assert r.status_code == 403
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_admin_proofs_run_unknown_scenario_400(client):
    """POST /v1/admin/proofs/run with unknown label returns 400."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.post(
            "/v1/admin/proofs/run",
            json={"label": "nonexistent_scenario"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert r.status_code == 400
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_admin_proofs_run_starts_run_when_workspace_has_runner(client):
    """POST /v1/admin/proofs/run with valid label and admin key returns run_id, folder, status."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    # Ensure workspace points to repo so scripts/run_proofs.py exists
    repo_root = Path(__file__).resolve().parent.parent
    os.environ["HG_WORKSPACE"] = str(repo_root)
    try:
        r = client.post(
            "/v1/admin/proofs/run",
            json={"label": "ticket_triage_5"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
        # 200 with run_id if runner exists; 503 if runner not found
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.json()
            assert "run_id" in data
            assert "folder" in data
            assert data.get("status") == "running"
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)
        os.environ.pop("HG_WORKSPACE", None)


def test_admin_proofs_runs_run_id_requires_admin_key(client):
    """GET /v1/admin/proofs/runs/{run_id} without X-Admin-Key returns 403."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.get("/v1/admin/proofs/runs/some-run-id")
        assert r.status_code == 403
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_admin_proofs_runs_run_id_404_for_unknown(client):
    """GET /v1/admin/proofs/runs/{run_id} for non-existent run returns 404."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.get(
            "/v1/admin/proofs/runs/nonexistent_run_12345",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert r.status_code == 404
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)
