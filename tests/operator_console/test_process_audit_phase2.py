"""
Layer 9 Phase 2: Operator console process audit API.
"""
import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from fastapi.testclient import TestClient
from app.main import app
from app.services import process_audit_service


def test_process_audit_get_requires_param(tmp_path, monkeypatch):
    monkeypatch.setattr(process_audit_service, "_workspace_root", lambda: tmp_path)
    client = TestClient(app)
    r = client.get("/api/v1/process-audit", headers={"Authorization": "Bearer test-api-key"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False
    assert "decision_id or run_id" in (data.get("error") or "")


def test_process_audit_post_runs_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(process_audit_service, "_workspace_root", lambda: tmp_path)
    client = TestClient(app)
    r = client.post(
        "/api/v1/process-audit",
        json={"decision_id": "dec-oc", "emit_ledger": False},
        headers={"Authorization": "Bearer test-api-key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "result" in data
    assert data["result"].get("decision_id") == "dec-oc"
