"""API tests for Operator Console steering endpoints (spec: docs/specs/operator_console_steering_api_spec.md)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from hg_gateway.shared_storage import append_steering_telemetry

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    _client_fixture = lambda: TestClient(app)
else:
    _client_fixture = None


def _api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


@pytest.fixture
def steering_workspace(tmp_path):
    """Create memory/overseer layout under tmp_path for steering tests."""
    overseer = tmp_path / "memory" / "overseer"
    overseer.mkdir(parents=True)
    (overseer / "authority-config.json").write_text(
        json.dumps({"mode": "moderate", "thresholds": {"max_edits": 5}, "task_file_editing_enabled": True}),
        encoding="utf-8",
    )
    steering_dir = overseer / "steering"
    steering_dir.mkdir()
    (steering_dir / "foo.json").write_text(json.dumps({"name": "foo", "role": "writer"}), encoding="utf-8")
    (steering_dir / "bar.json").write_text(json.dumps({"name": "bar"}), encoding="utf-8")
    return tmp_path


def test_steering_events_requires_auth(client):
    """GET /api/v1/steering/events without auth returns 401 or 403."""
    r = client.get("/api/v1/steering/events")
    assert r.status_code in (401, 403)


def test_steering_events_empty(client):
    """GET /api/v1/steering/events with no workspace returns ok and empty events."""
    with patch("app.services.steering_service._workspace_root", return_value=None):
        r = client.get("/api/v1/steering/events", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("events") == []


def test_steering_events_with_data(client, steering_workspace):
    """GET /api/v1/steering/events returns newest-first events from steering_events.jsonl."""
    with (
        patch("app.services.steering_service._workspace_root", return_value=steering_workspace),
        patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(steering_workspace / "memory" / "gateway.sqlite3")}, clear=False),
        patch("hg_lib.config.get_workspace_root", return_value=steering_workspace),
    ):
        append_steering_telemetry("cycle_start", {"timestamp":"2025-01-01T12:00:00Z","event":"cycle_start","agent_id":"a1"})
        append_steering_telemetry("cycle_end", {"timestamp":"2025-01-01T12:01:00Z","event":"cycle_end","agent_id":"a1","run_id":"r1"})
        r = client.get("/api/v1/steering/events", headers=_api_headers(), params={"limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    events = data.get("events", [])
    assert len(events) == 2
    assert events[0].get("event") == "cycle_end"
    assert events[0].get("run_id") == "r1"
    assert events[1].get("event") == "cycle_start"


def test_steering_events_limit(client, steering_workspace):
    """GET /api/v1/steering/events?limit=1 returns at most 1 event."""
    with (
        patch("app.services.steering_service._workspace_root", return_value=steering_workspace),
        patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(steering_workspace / "memory" / "gateway.sqlite3")}, clear=False),
        patch("hg_lib.config.get_workspace_root", return_value=steering_workspace),
    ):
        append_steering_telemetry("cycle_start", {"timestamp":"2025-01-01T12:00:00Z","event":"cycle_start","agent_id":"a1"})
        r = client.get("/api/v1/steering/events", headers=_api_headers(), params={"limit": 1})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert len(data.get("events", [])) == 1


def test_steering_authority_config_requires_auth(client):
    """GET /api/v1/steering/authority-config without auth returns 401 or 403."""
    r = client.get("/api/v1/steering/authority-config")
    assert r.status_code in (401, 403)


def test_steering_authority_config_default(client):
    """GET /api/v1/steering/authority-config with no workspace returns default config."""
    with patch("app.services.steering_service._workspace_root", return_value=None):
        r = client.get("/api/v1/steering/authority-config", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("config", {}).get("mode") == "moderate"
    assert "thresholds" in data.get("config", {})


def test_steering_authority_config_with_data(client, steering_workspace):
    """GET /api/v1/steering/authority-config returns file content when present."""
    with patch("app.services.steering_service._workspace_root", return_value=steering_workspace):
        r = client.get("/api/v1/steering/authority-config", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("config", {}).get("mode") == "moderate"
    assert data.get("config", {}).get("task_file_editing_enabled") is True


def test_steering_profiles_requires_auth(client):
    """GET /api/v1/steering/profiles without auth returns 401 or 403."""
    r = client.get("/api/v1/steering/profiles")
    assert r.status_code in (401, 403)


def test_steering_profiles_empty(client):
    """GET /api/v1/steering/profiles with no workspace returns ok and empty list."""
    with (
        patch("app.services.steering_service._workspace_root", return_value=None),
        patch("hg_core.job_registry.list_tasks", return_value=[]),
    ):
        r = client.get("/api/v1/steering/profiles", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("profiles") == []


def test_steering_profiles_list(client, steering_workspace):
    """GET /api/v1/steering/profiles returns list of profile IDs (basenames without .json)."""
    with (
        patch("app.services.steering_service._workspace_root", return_value=steering_workspace),
        patch("hg_core.job_registry.list_tasks", return_value=[]),
    ):
        r = client.get("/api/v1/steering/profiles", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    profiles = data.get("profiles", [])
    assert set(profiles) == {"foo", "bar"}


def test_steering_profile_detail_requires_auth(client):
    """GET /api/v1/steering/profiles/{id} without auth returns 401 or 403."""
    r = client.get("/api/v1/steering/profiles/foo")
    assert r.status_code in (401, 403)


def test_steering_profile_detail_found(client, steering_workspace):
    """GET /api/v1/steering/profiles/foo returns profile when file exists."""
    with patch("app.services.steering_service._workspace_root", return_value=steering_workspace):
        r = client.get("/api/v1/steering/profiles/foo", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("agent_id") == "foo"
    assert data.get("profile", {}).get("heat") == 0.5
    assert data.get("profile", {}).get("target_policy") == "mixed"


def test_steering_profile_detail_not_found(client, steering_workspace):
    """GET /api/v1/steering/profiles/nonexistent returns default profile."""
    with patch("app.services.steering_service._workspace_root", return_value=steering_workspace):
        r = client.get("/api/v1/steering/profiles/nonexistent", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("profile", {}).get("target_policy") == "mixed"
