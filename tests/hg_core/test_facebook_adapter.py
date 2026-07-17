from __future__ import annotations

import sqlite3
import shutil
import uuid
from pathlib import Path
from typing import Optional

import pytest

from hg_core.security.keystore import KeystoreService
from hg_core.security.social_account_artifacts import record_social_account_session_binding
from hg_core.security.secrets_provider import SecretsProvider
from hg_core.social.facebook_adapter import (
    FacebookAdapter,
    build_notifications_digest,
    detect_facebook_login_state,
    extract_facebook_notifications,
    parse_facebook_login_secret,
)
from hg_gateway import keystore_repo


class DictSecretsProvider(SecretsProvider):
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get(self, key: str) -> Optional[str]:
        return self._values.get(key)


class FakeRuntime:
    def __init__(self, *, mode: str = "success") -> None:
        self.mode = mode
        self.session_id = "session-1"
        self.state = {"current_url": "about:blank", "state": "active", "platform": "facebook"}
        self.html = """
        <html><body>
        <form>
          <input name="email" autocomplete="username" />
          <input name="pass" autocomplete="current-password" />
          <button name="login">Log In</button>
        </form>
        </body></html>
        """
        self.values: dict[str, str] = {}
        self.paused = False
        self.notification_digest_payload = None
        self.start_calls = 0
        self.artifacts_by_session: dict[str, list[dict]] = {}

    def start_session(self, entity_id: str, platform: str, tenant_id: str = "default") -> str:
        self.start_calls += 1
        return self.session_id

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
                  <li data-notification-kind="like">
                    <span class="actor">Bob</span>
                    <span class="title">liked your update</span>
                    <span class="snippet">Thumbs up</span>
                    <span class="timestamp">5m</span>
                    <a href="https://facebook.com/n2">Open</a>
                  </li>
                </ul>
              </body>
            </html>
            """
        return type("R", (), {"ok": True, "data": {"url": url}})()

    def capture(self, session_id: str, label: str, tenant_id: str = "default"):
        path = str(Path(".") / f"{label}.png")
        snap = str(Path(".") / f"{label}.json")
        return type("R", (), {"ok": True, "screenshot_path": path, "snapshot_path": snap, "data": {"label": label}})()

    def fill(self, session_id: str, selector: str, value: str, tenant_id: str = "default"):
        self.values[selector] = value
        return type("R", (), {"ok": True, "data": {"selector": selector}})()

    def click(self, session_id: str, selector: str, tenant_id: str = "default"):
        if self.mode == "success":
            self.html = """
            <html data-authenticated-user="fb-main">
              <body>
                <a href="/notifications" aria-label="Notifications">Notifications</a>
              </body>
            </html>
            """
            self.state["current_url"] = "https://www.facebook.com/home"
        elif self.mode == "challenge":
            self.html = "<html><body>Checkpoint Security Check</body></html>"
            self.state["current_url"] = "https://www.facebook.com/checkpoint/"
        elif self.mode == "wrong_account":
            self.html = """
            <html data-authenticated-user="someone-else">
              <body>
                <a href="/notifications" aria-label="Notifications">Notifications</a>
              </body>
            </html>
            """
            self.state["current_url"] = "https://www.facebook.com/home"
        return type("R", (), {"ok": True, "data": {"selector": selector}})()

    def get_page_content(self, session_id: str, tenant_id: str = "default") -> str:
        return self.html

    def get_session_state(self, session_id: str, tenant_id: str = "default"):
        return self.state

    def list_artifacts(self, session_id: str, tenant_id: str = "default"):
        return list(self.artifacts_by_session.get(session_id, []))

    def pause_for_human_gate(self, session_id: str, reason: str, tenant_id: str = "default"):
        self.paused = True
        self.state["state"] = "awaiting_human"

    def write_json_artifact(
        self,
        session_id: str,
        label: str,
        payload: dict,
        *,
        artifact_type: str = "snapshot",
        tenant_id: str = "default",
    ) -> str:
        self.notification_digest_payload = payload
        return str(Path(".") / f"{label}.json")


@pytest.fixture
def gateway_db(monkeypatch):
    root = Path(".pytest-tmp-facebook") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    try:
        yield db_path
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_parse_facebook_login_secret_pipe():
    secret = parse_facebook_login_secret("user@example.com|password123")
    assert secret.identifier == "user@example.com"
    assert secret.password == "password123"


def test_detect_facebook_login_states():
    login_state = detect_facebook_login_state(
        '<input name="email" /><input name="pass" /><button name="login">Log In</button>',
        "https://www.facebook.com/",
    )
    assert login_state["state"] == "login_required"

    challenge_state = detect_facebook_login_state(
        "<html>Checkpoint Security Check</html>",
        "https://www.facebook.com/checkpoint/",
    )
    assert challenge_state["state"] == "challenge"

    logged_in = detect_facebook_login_state(
        '<html data-authenticated-user="fb-main"><a href="/notifications" aria-label="Notifications">Notifications</a></html>',
        "https://www.facebook.com/home",
        expected_account_alias="fb-main",
    )
    assert logged_in["state"] == "logged_in"

    wrong = detect_facebook_login_state(
        '<html data-authenticated-user="someone-else"><a href="/notifications" aria-label="Notifications">Notifications</a></html>',
        "https://www.facebook.com/home",
        expected_account_alias="fb-main",
    )
    assert wrong["state"] == "wrong_account"


def test_extract_notifications_and_digest():
    html = """
    <ul>
      <li data-notification-kind="comment">
        <span class="actor">Alice</span>
        <span class="title">commented on your post</span>
        <span class="snippet">Nice work</span>
        <span class="timestamp">1m</span>
        <a href="https://facebook.com/n1">Open</a>
      </li>
      <li data-notification-kind="like">
        <span class="actor">Bob</span>
        <span class="title">liked your update</span>
        <span class="snippet">Thumbs up</span>
        <span class="timestamp">5m</span>
        <a href="https://facebook.com/n2">Open</a>
      </li>
    </ul>
    """
    items = extract_facebook_notifications(html, limit=10)
    assert len(items) == 2
    assert items[0]["actor"] == "Alice"
    assert items[0]["kind"] == "comment"
    digest = build_notifications_digest(items)
    assert "Alice: commented on your post" in digest
    assert "Bob: liked your update" in digest


def test_facebook_adapter_login_success(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    adapter = FacebookAdapter(
        runtime=FakeRuntime(mode="success"),
        keystore=KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"})),
    )

    result = adapter.login(tenant_id="tenant-a", entity_id="entity-1", account_alias="fb-main")
    assert result["state"] == "logged_in"
    assert result["login_performed"] is True
    assert result["account_proof_artifact"]["artifact_type"] == "verification_proof"
    account = keystore_repo.social_account_get("acct-1", tenant_id="tenant-a", db_path=str(gateway_db))
    assert account["state"] == "verified"
    with sqlite3.connect(gateway_db) as conn:
        rows = conn.execute(
            "SELECT artifact_type FROM proof_artifacts WHERE related_kind = 'social_account' AND related_id = ?",
            ("acct-1",),
        ).fetchall()
    assert rows
    assert "verification_proof" in {row[0] for row in rows}


def test_facebook_adapter_login_challenge_pauses(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    runtime = FakeRuntime(mode="challenge")
    adapter = FacebookAdapter(
        runtime=runtime,
        keystore=KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"})),
    )

    result = adapter.login(tenant_id="tenant-a", entity_id="entity-1", account_alias="fb-main")
    assert result["state"] == "challenge"
    assert runtime.paused is True
    assert result["account_proof_artifact"]["artifact_type"] == "account_proof"
    account = keystore_repo.social_account_get("acct-1", tenant_id="tenant-a", db_path=str(gateway_db))
    assert account["state"] == "challenged"


def test_facebook_adapter_read_notifications(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    runtime = FakeRuntime(mode="success")
    adapter = FacebookAdapter(
        runtime=runtime,
        keystore=KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"})),
    )

    result = adapter.read_notifications(
        tenant_id="tenant-a",
        entity_id="entity-1",
        account_alias="fb-main",
        limit=10,
    )
    assert result["state"] == "logged_in"
    assert result["notification_count_visible"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["actor"] == "Alice"
    assert "Alice: commented on your post" in result["digest_text"]
    assert runtime.notification_digest_payload is not None


def test_facebook_adapter_reuses_existing_session_for_login(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    runtime = FakeRuntime(mode="success")
    profile_dir = gateway_db.parent / "reusable-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    runtime.artifacts_by_session["session-reused"] = [
        {"artifact_type": "profile_dir", "path": str(profile_dir)},
    ]
    record_social_account_session_binding(
        "acct-1",
        browser_session_id="session-reused",
        platform="facebook",
        tenant_id="tenant-a",
        entity_id="entity-1",
        account_alias="fb-main",
        state="active",
    )
    adapter = FacebookAdapter(
        runtime=runtime,
        keystore=KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"})),
    )

    result = adapter.login(tenant_id="tenant-a", entity_id="entity-1", account_alias="fb-main")
    assert result["browser_session_id"] == "session-reused"
    assert runtime.start_calls == 0


def test_facebook_adapter_reuses_existing_session_for_notifications(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    runtime = FakeRuntime(mode="success")
    profile_dir = gateway_db.parent / "reusable-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    runtime.artifacts_by_session["session-reused"] = [
        {"artifact_type": "profile_dir", "path": str(profile_dir)},
    ]
    runtime.html = """
    <html data-authenticated-user="fb-main">
      <body><a href="/notifications" aria-label="Notifications">Notifications</a></body>
    </html>
    """
    runtime.state["current_url"] = "https://www.facebook.com/home"
    record_social_account_session_binding(
        "acct-1",
        browser_session_id="session-reused",
        platform="facebook",
        tenant_id="tenant-a",
        entity_id="entity-1",
        account_alias="fb-main",
        state="active",
    )
    adapter = FacebookAdapter(
        runtime=runtime,
        keystore=KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"})),
    )

    result = adapter.read_notifications(
        tenant_id="tenant-a",
        entity_id="entity-1",
        account_alias="fb-main",
        limit=10,
    )
    assert result["browser_session_id"] == "session-reused"
    assert runtime.start_calls == 0


def test_facebook_adapter_does_not_reuse_degraded_bound_session(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    runtime = FakeRuntime(mode="success")
    runtime.artifacts_by_session["session-reused"] = [
        {"artifact_type": "profile_dir", "path": str(gateway_db.parent / "missing-profile-dir")},
    ]
    record_social_account_session_binding(
        "acct-1",
        browser_session_id="session-reused",
        platform="facebook",
        tenant_id="tenant-a",
        entity_id="entity-1",
        account_alias="fb-main",
        state="active",
    )
    with sqlite3.connect(gateway_db) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-reused", "tenant-a", "entity-1", "facebook", "active"),
        )
        conn.commit()
    adapter = FacebookAdapter(
        runtime=runtime,
        keystore=KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"})),
    )

    result = adapter.login(tenant_id="tenant-a", entity_id="entity-1", account_alias="fb-main")
    assert result["browser_session_id"] == "session-1"
    assert runtime.start_calls == 1
    assert result["replaced_degraded_session"]["browser_session_id"] == "session-reused"
    assert result["replaced_degraded_session"]["reason"] == "missing_restart_critical_browser_artifacts"
    assert "missing_profile_dir" in result["replaced_degraded_session"]["previous_health"]["issues"]
    with sqlite3.connect(gateway_db) as conn:
        row = conn.execute(
            "SELECT state FROM browser_sessions WHERE browser_session_id = ? AND tenant_id = ?",
            ("session-reused", "tenant-a"),
        ).fetchone()
        artifact = conn.execute(
            """SELECT artifact_type, path
               FROM proof_artifacts
               WHERE related_kind = 'browser_session' AND related_id = ? AND artifact_type = 'session_degraded'
               ORDER BY created_at DESC, proof_id DESC
               LIMIT 1""",
            ("session-reused",),
        ).fetchone()
    assert row[0] == "degraded"
    assert artifact[0] == "session_degraded"
    assert artifact[1] == "missing_restart_critical_browser_artifacts"
