"""
Backend proof service E2E: POST run (with use_fixtures), poll until completed, verify folder and index. No mocks.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
POLL_INTERVAL = 0.5
POLL_TIMEOUT = 90


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_proofs_run_without_admin_key_returns_403_or_503(client):
    """POST /v1/admin/proofs/run without X-Admin-Key returns 403 or 503."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    try:
        r = client.post(
            "/v1/admin/proofs/run",
            json={"label": "weather_sweep_10"},
        )
        assert r.status_code in (403, 503)
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_admin_proofs_run_weather_sweep_10_completes_and_index_updated(client):
    """
    E2E: POST run weather_sweep_10 with use_fixtures; poll until completed;
    verify folder has summary.json and WEATHER_SUMMARY_10_PROVINCES.md; index updated.
    """
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "test-admin-key"
    os.environ["HG_GATEWAY_API_KEY"] = "test-api-key"
    os.environ["HG_WORKSPACE"] = str(REPO_ROOT)
    try:
        r = client.post(
            "/v1/admin/proofs/run",
            json={
                "label": "weather_sweep_10",
                "params": {"use_fixtures": True},
            },
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        run_id = data["run_id"]
        folder = data["folder"]
        assert data["status"] == "running"

        run_dir = Path(folder)
        assert run_dir.is_dir()

        # Poll until completed
        for _ in range(int(POLL_TIMEOUT / POLL_INTERVAL)):
            r2 = client.get(
                f"/v1/admin/proofs/runs/{run_id}",
                headers={"X-Admin-Key": "test-admin-key"},
            )
            assert r2.status_code == 200
            status_data = r2.json()
            if status_data.get("status") == "completed":
                break
            time.sleep(POLL_INTERVAL)
        else:
            pytest.fail("Run did not complete within %s seconds" % POLL_TIMEOUT)

        assert (run_dir / "summary.json").exists()
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary.get("checks_passed") is True
        assert summary.get("label") == "weather_sweep_10"

        assert (run_dir / "WEATHER_SUMMARY_10_PROVINCES.md").exists()
        md = (run_dir / "WEATHER_SUMMARY_10_PROVINCES.md").read_text(encoding="utf-8")
        assert "province" in md.lower() or "weather" in md.lower() or len(md.strip()) > 0

        r3 = client.get(
            "/v1/admin/proofs/index",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert r3.status_code == 200
        index = r3.json()
        assert "latest" in index
        assert index["latest"].get("weather_sweep_10") == folder
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_WORKSPACE", None)
