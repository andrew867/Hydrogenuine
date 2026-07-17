from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

from hg_core.browser import playwright_runtime

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    app = None
    TestClient = None


class _FakeResponse:
    status = 200


class _FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"

    def goto(self, url: str, wait_until: str = "domcontentloaded"):
        self.url = url
        return _FakeResponse()

    def screenshot(self, path: str, full_page: bool = True):
        Path(path).write_bytes(b"png")

    def content(self) -> str:
        return f"<html>{self.url}</html>"


class _FakeTracing:
    def start(self, screenshots: bool = True, snapshots: bool = True):
        return None

    def stop(self, path: str):
        Path(path).write_bytes(b"trace")


class _FakeContext:
    def __init__(self) -> None:
        self.tracing = _FakeTracing()
        self.pages = [_FakePage()]

    def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page

    def close(self):
        return None


class _FakeChromium:
    def launch_persistent_context(self, user_data_dir: str, headless: bool = True, viewport=None):
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        return _FakeContext()


class _FakePlaywrightManager:
    def __init__(self) -> None:
        self.chromium = _FakeChromium()

    def stop(self):
        return None


class _FakeSyncPlaywright:
    def start(self):
        return _FakePlaywrightManager()


def _headers():
    return {"Authorization": "Bearer test-api-key", "X-Tenant-ID": "tenant-a"}


@pytest.fixture
def client(monkeypatch):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    root = Path(".pytest-tmp-browser-api") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "gateway.sqlite3"
    artifacts = root / "artifacts"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_BROWSER_ARTIFACTS_DIR", str(artifacts))
    monkeypatch.setattr("hg_core.browser._playwright_impl.sync_playwright", lambda: _FakeSyncPlaywright())
    monkeypatch.setattr(playwright_runtime, "_RUNTIME", None)
    try:
        yield TestClient(app), artifacts
    finally:
        playwright_runtime._RUNTIME = None
        shutil.rmtree(root, ignore_errors=True)


def test_browser_session_api_flow(client):
    test_client, artifacts = client

    create_response = test_client.post(
        "/api/v1/browser-sessions",
        headers=_headers(),
        json={"entity_id": "entity-1", "platform": "facebook"},
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["browser_session_id"]

    navigate_response = test_client.post(
        f"/api/v1/browser-sessions/{session_id}/navigate",
        headers=_headers(),
        json={"url": "https://example.com"},
    )
    assert navigate_response.status_code == 200
    assert navigate_response.json()["session"]["current_url"] == "https://example.com"

    capture_response = test_client.post(
        f"/api/v1/browser-sessions/{session_id}/capture",
        headers=_headers(),
        json={"label": "homepage"},
    )
    assert capture_response.status_code == 200
    assert Path(capture_response.json()["screenshot_path"]).exists()
    assert Path(capture_response.json()["snapshot_path"]).exists()

    pause_response = test_client.post(
        f"/api/v1/browser-sessions/{session_id}/pause",
        headers=_headers(),
        json={"reason": "login_required"},
    )
    assert pause_response.status_code == 200

    state_response = test_client.get(
        f"/api/v1/browser-sessions/{session_id}",
        headers=_headers(),
    )
    assert state_response.status_code == 200
    assert state_response.json()["state"] == "awaiting_human"

    resume_response = test_client.post(
        f"/api/v1/browser-sessions/{session_id}/resume",
        headers=_headers(),
    )
    assert resume_response.status_code == 200

    artifacts_response = test_client.get(
        f"/api/v1/browser-sessions/{session_id}/artifacts",
        headers=_headers(),
    )
    assert artifacts_response.status_code == 200
    artifact_paths = [item["path"] for item in artifacts_response.json()["items"]]
    assert str((artifacts / session_id / "homepage.png").resolve()) in artifact_paths
    assert str((artifacts / session_id / "homepage.json").resolve()) in artifact_paths
