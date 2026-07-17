from __future__ import annotations

import sqlite3
import shutil
import sys
import uuid
from pathlib import Path

import pytest

from hg_core.social.facebook_adapter import FacebookAdapter
from hg_gateway import keystore_repo

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import social_entity
else:
    app = None
    TestClient = None


class FakeRuntime:
    def __init__(self, *, mode: str) -> None:
        self.mode = mode
        self.session_id = f"session-{mode}"
        self.state = {"current_url": "about:blank", "state": "active", "platform": "facebook"}
        self.html = """
        <html><body>
        <input name="email" autocomplete="username" />
        <input name="pass" autocomplete="current-password" />
        <button name="login">Log In</button>
        </body></html>
        """
        self.paused = False
        self.digest_payload = None
        self.reusable_session_id = None
        self.artifacts_by_session = {}

    def start_session(self, entity_id: str, platform: str, tenant_id: str = "default") -> str:
        return self.session_id

    def find_reusable_session(
        self,
        entity_id: str,
        platform: str,
        *,
        tenant_id: str = "default",
        allowed_states=None,
    ):
        if not self.reusable_session_id:
            return None
        return {
            "browser_session_id": self.reusable_session_id,
            "tenant_id": tenant_id,
            "entity_id": entity_id,
            "platform": platform,
            "state": "active",
        }

    def navigate(self, session_id: str, url: str, tenant_id: str = "default"):
        self.state["current_url"] = url
        if "notifications" in url and self.mode == "success":
            self.html = """
            <html data-authenticated-user="fb-main">
              <body>
                <a href="/notifications" aria-label="Notifications">Notifications</a>
                <ul id="notifications_list">
                  <li data-notification-kind="comment">
                    <span class="actor">Alice</span>
                    <span class="title">commented on your post</span>
                    <span class="snippet">Nice work</span>
                    <span class="timestamp">1m</span>
                    <a href="https://facebook.com/n1">Open</a>
                  </li>
                </ul>
              </body>
            </html>
            """
        return type("R", (), {"ok": True, "data": {"url": url}})()

    def capture(self, session_id: str, label: str, tenant_id: str = "default"):
        return type(
            "R",
            (),
            {
                "ok": True,
                "screenshot_path": str(Path(".") / f"{label}.png"),
                "snapshot_path": str(Path(".") / f"{label}.json"),
                "data": {"label": label},
            },
        )()

    def fill(self, session_id: str, selector: str, value: str, tenant_id: str = "default"):
        return type("R", (), {"ok": True, "data": {}})()

    def click(self, session_id: str, selector: str, tenant_id: str = "default"):
        if self.mode == "success":
            self.html = """
            <html data-authenticated-user="fb-main">
              <body><a href="/notifications" aria-label="Notifications">Notifications</a></body>
            </html>
            """
            self.state["current_url"] = "https://www.facebook.com/home"
        else:
            self.html = "<html><body>Checkpoint Security Check</body></html>"
            self.state["current_url"] = "https://www.facebook.com/checkpoint/"
        return type("R", (), {"ok": True, "data": {}})()

    def get_page_content(self, session_id: str, tenant_id: str = "default") -> str:
        return self.html

    def get_session_state(self, session_id: str, tenant_id: str = "default"):
        return self.state

    def list_artifacts(self, session_id: str, tenant_id: str = "default"):
        return list(self.artifacts_by_session.get(session_id, []))

    def pause_for_human_gate(self, session_id: str, reason: str, tenant_id: str = "default"):
        self.paused = True
        self.state["state"] = "awaiting_human"

    def write_json_artifact(self, session_id: str, label: str, payload: dict, *, artifact_type: str = "snapshot", tenant_id: str = "default"):
        self.digest_payload = payload
        return str(Path(".") / f"{label}.json")


def _headers():
    return {"Authorization": "Bearer test-api-key", "X-Tenant-ID": "tenant-a"}


@pytest.fixture
def client(monkeypatch):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    root = Path(".pytest-tmp-social-facebook-api") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_FB_LOGIN_SECRET", "user@example.com|password123")
    try:
        yield TestClient(app), db_path
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _seed_account(db_path: Path):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(db_path),
    )


def test_facebook_login_api_success(client, monkeypatch):
    test_client, db_path = client
    _seed_account(db_path)
    runtime = FakeRuntime(mode="success")
    monkeypatch.setattr(
        social_entity,
        "FacebookAdapter",
        lambda: FacebookAdapter(runtime=runtime),
    )
    response = test_client.post(
        "/api/v1/social-entity/facebook/login",
        headers=_headers(),
        json={"entity_id": "entity-1", "account_alias": "fb-main"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "logged_in"
    assert payload["login_performed"] is True
    assert payload["browser_session_id"] == "session-success"


def test_facebook_login_api_challenge(client, monkeypatch):
    test_client, db_path = client
    _seed_account(db_path)
    runtime = FakeRuntime(mode="challenge")
    monkeypatch.setattr(
        social_entity,
        "FacebookAdapter",
        lambda: FacebookAdapter(runtime=runtime),
    )
    response = test_client.post(
        "/api/v1/social-entity/facebook/login",
        headers=_headers(),
        json={"entity_id": "entity-1", "account_alias": "fb-main"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "challenge"
    assert payload["browser_session_id"] == "session-challenge"
    assert runtime.paused is True


def test_facebook_notifications_api_success(client, monkeypatch):
    test_client, db_path = client
    _seed_account(db_path)
    runtime = FakeRuntime(mode="success")
    monkeypatch.setattr(
        social_entity,
        "FacebookAdapter",
        lambda: FacebookAdapter(runtime=runtime),
    )
    response = test_client.post(
        "/api/v1/social-entity/facebook/read-notifications",
        headers=_headers(),
        json={"entity_id": "entity-1", "account_alias": "fb-main", "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "logged_in"
    assert payload["notification_count_visible"] == 1
    assert payload["items"][0]["actor"] == "Alice"
    assert "Alice: commented on your post" in payload["digest_text"]
    assert runtime.digest_payload is not None


def test_facebook_login_api_reports_replaced_degraded_session(client, monkeypatch):
    test_client, db_path = client
    _seed_account(db_path)
    runtime = FakeRuntime(mode="success")
    runtime.reusable_session_id = "session-reused"
    runtime.artifacts_by_session["session-reused"] = [
        {"artifact_type": "profile_dir", "path": str(db_path.parent / "missing-profile-dir")},
    ]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-reused", "tenant-a", "entity-1", "facebook", "active"),
        )
        conn.commit()
    from hg_core.security.social_account_artifacts import record_social_account_session_binding
    record_social_account_session_binding(
        "acct-1",
        browser_session_id="session-reused",
        platform="facebook",
        tenant_id="tenant-a",
        entity_id="entity-1",
        account_alias="fb-main",
        state="active",
    )
    monkeypatch.setattr(
        social_entity,
        "FacebookAdapter",
        lambda: FacebookAdapter(runtime=runtime),
    )
    response = test_client.post(
        "/api/v1/social-entity/facebook/login",
        headers=_headers(),
        json={"entity_id": "entity-1", "account_alias": "fb-main"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["browser_session_id"] == "session-success"
    assert payload["replaced_degraded_session"]["browser_session_id"] == "session-reused"
    assert payload["replaced_degraded_session"]["reason"] == "missing_restart_critical_browser_artifacts"
