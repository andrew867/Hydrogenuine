"""
Layer 8 Phase 4: Operator console repr-interp API (results + proof-path).
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
from app.services import repr_interp_service


def test_repr_interp_results_endpoint_returns_ok_shape(tmp_path, monkeypatch):
    """GET /api/v1/repr-interp/results returns { ok, results } when workspace is available."""
    monkeypatch.setattr(repr_interp_service, "_workspace_root", lambda: tmp_path)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/repr-interp/results",
        params={"limit": 10},
        headers={"Authorization": "Bearer test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_repr_interp_proof_path_endpoint_returns_ok_shape(tmp_path, monkeypatch):
    """GET /api/v1/repr-interp/decisions/{id}/proof-path returns { ok, proof_path }."""
    monkeypatch.setattr(repr_interp_service, "_workspace_root", lambda: tmp_path)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/repr-interp/decisions/some-decision-id/proof-path",
        headers={"Authorization": "Bearer test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "ok" in data
    assert "proof_path" in data
