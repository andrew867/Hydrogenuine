from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

# The Playwright browser runtime needs the (optional) playwright package.
pytest.importorskip("playwright.sync_api")

from hg_core.browser._playwright_impl import PlaywrightBrowserRuntime


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
        return f"<html><body>{self.url}</body></html>"


class _FakeTracing:
    def __init__(self) -> None:
        self.started = False

    def start(self, screenshots: bool = True, snapshots: bool = True):
        self.started = True

    def stop(self, path: str):
        Path(path).write_bytes(b"trace")


class _FakeContext:
    def __init__(self) -> None:
        self.tracing = _FakeTracing()
        self.pages = [_FakePage()]
        self.closed = False

    def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class _FakeChromium:
    def launch_persistent_context(self, user_data_dir: str, headless: bool = True, viewport=None):
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        return _FakeContext()


class _FakePlaywrightManager:
    def __init__(self) -> None:
        self.chromium = _FakeChromium()
        self.stopped = False

    def stop(self):
        self.stopped = True


class _FakeSyncPlaywright:
    def start(self):
        return _FakePlaywrightManager()


@pytest.fixture
def runtime_env(monkeypatch):
    root = Path(".pytest-tmp-browser") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "gateway.sqlite3"
    artifacts = root / "artifacts"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_BROWSER_ARTIFACTS_DIR", str(artifacts))
    try:
        yield root, db_path, artifacts
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_playwright_runtime_session_lifecycle(monkeypatch, runtime_env):
    _root, _db_path, artifacts = runtime_env
    monkeypatch.setattr("hg_core.browser._playwright_impl.sync_playwright", lambda: _FakeSyncPlaywright())
    runtime = PlaywrightBrowserRuntime()

    session_id = runtime.start_session("entity-1", "facebook", tenant_id="tenant-a")
    state = runtime.get_session_state(session_id, tenant_id="tenant-a")
    assert state is not None
    assert state["entity_id"] == "entity-1"
    assert state["platform"] == "facebook"
    assert state["current_url"] == "about:blank"

    nav = runtime.navigate(session_id, "https://example.com", tenant_id="tenant-a")
    assert nav.ok is True
    assert nav.data["url"] == "https://example.com"

    capture = runtime.capture(session_id, "home", tenant_id="tenant-a")
    assert capture.ok is True
    assert Path(capture.screenshot_path).exists()
    assert Path(capture.snapshot_path).exists()

    runtime.pause_for_human_gate(session_id, "login_required", tenant_id="tenant-a")
    state = runtime.get_session_state(session_id, tenant_id="tenant-a")
    assert state["state"] == "awaiting_human"

    runtime.resume_session(session_id, tenant_id="tenant-a")
    state = runtime.get_session_state(session_id, tenant_id="tenant-a")
    assert state["state"] == "active"

    runtime.close_session(session_id, tenant_id="tenant-a")
    state = runtime.get_session_state(session_id, tenant_id="tenant-a")
    assert state["state"] == "closed"
    assert Path(state["trace_path"]).exists()

    artifact_paths = [item["path"] for item in runtime.list_artifacts(session_id, tenant_id="tenant-a")]
    assert str((artifacts / session_id / "home.png").resolve()) in artifact_paths
    assert str((artifacts / session_id / "home.json").resolve()) in artifact_paths
    assert str((artifacts / session_id / "trace.zip").resolve()) in artifact_paths


def test_playwright_runtime_restores_persisted_session(monkeypatch, runtime_env):
    _root, _db_path, artifacts = runtime_env
    monkeypatch.setattr("hg_core.browser._playwright_impl.sync_playwright", lambda: _FakeSyncPlaywright())

    first_runtime = PlaywrightBrowserRuntime()
    session_id = first_runtime.start_session("entity-1", "facebook", tenant_id="tenant-a")
    first_runtime.navigate(session_id, "https://example.com/login", tenant_id="tenant-a")
    first_runtime.capture(session_id, "before-restart", tenant_id="tenant-a")

    restored_runtime = PlaywrightBrowserRuntime()
    state = restored_runtime.get_session_state(session_id, tenant_id="tenant-a")
    assert state is not None
    assert str((artifacts / session_id / "profile").resolve()) == state["profile_dir"]

    restored_runtime.capture(session_id, "after-restart", tenant_id="tenant-a")
    artifacts_for_session = restored_runtime.list_artifacts(session_id, tenant_id="tenant-a")
    artifact_types = [item["artifact_type"] for item in artifacts_for_session]
    assert "session_restore" in artifact_types
    assert str((artifacts / session_id / "after-restart.png").resolve()) in [item["path"] for item in artifacts_for_session]
