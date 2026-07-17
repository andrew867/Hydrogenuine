from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

from hg_gateway import keystore_repo
from hg_core.browser import playwright_runtime
from hg_core.human_notifications import record_human_notification
from hg_gateway.db import _get_db_path, get_connection

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


def _headers():
    return {"Authorization": "Bearer test-api-key", "X-Tenant-ID": "tenant-a"}


@pytest.fixture
def client(monkeypatch):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    root = Path(".pytest-tmp-keystore-api") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "gateway.sqlite3"
    artifacts = root / "artifacts"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_BROWSER_ARTIFACTS_DIR", str(artifacts))
    monkeypatch.setenv("HG_FB_LOGIN_SECRET", "user@example.com|password123")
    monkeypatch.setenv("HG_FB_MFA_SECRET", "123456")
    monkeypatch.setattr(playwright_runtime, "_RUNTIME", None)
    try:
        yield TestClient(app), db_path
    finally:
        playwright_runtime._RUNTIME = None
        shutil.rmtree(root, ignore_errors=True)


def test_create_account_attach_verify_and_lock(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()["item"]
    social_account_id = created["social_account_id"]
    assert created["state"] == "unverified"

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    keystore_repo.secret_alias_create(
        alias_id="alias-mfa",
        provider_kind="env",
        provider_ref="fb_mfa_secret",
        purpose="facebook_mfa",
        db_path=str(db_path),
    )

    attach_login = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )
    assert attach_login.status_code == 200
    assert attach_login.json()["item"]["login_secret_alias_id"] == "alias-login"

    attach_mfa = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "mfa", "alias_id": "alias-mfa"},
    )
    assert attach_mfa.status_code == 200
    assert attach_mfa.json()["item"]["mfa_secret_alias_id"] == "alias-mfa"

    verify_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/verify-login",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    assert verify_response.status_code == 200
    verified = verify_response.json()
    assert verified["verified"] is True
    assert verified["state"] == "verified"
    assert verified["login_secret_present"] is True
    assert verified["mfa_secret_present"] is True
    assert verified["artifact"]["artifact_type"] == "verification_proof"

    lock_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/lock",
        headers=_headers(),
    )
    assert lock_response.status_code == 200
    assert lock_response.json()["item"]["state"] == "locked"


def test_start_login_session_creates_browser_session(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )

    response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "facebook"
    assert payload["account_alias"] == "fb-main"
    assert payload["browser_session_id"]

    session_state = test_client.get(
        f"/api/v1/browser-sessions/{payload['browser_session_id']}",
        headers=_headers(),
    )
    assert session_state.status_code == 200
    assert session_state.json()["platform"] == "facebook"
    assert session_state.json()["entity_id"] == "entity-1"


def test_start_login_session_reuses_existing_active_session(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )

    first = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    second = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["browser_session_id"] == second.json()["browser_session_id"]


def test_verify_login_missing_secret_returns_422(client):
    test_client, _db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/verify-login",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    assert response.status_code == 422
    assert "missing a login secret alias" in response.json()["detail"]


def test_account_overview_includes_latest_notification_digest(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )

    session_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    session_id = session_response.json()["browser_session_id"]

    runtime = __import__("hg_core.browser.playwright_runtime", fromlist=["get_playwright_runtime"]).get_playwright_runtime()
    runtime.write_json_artifact(
        session_id,
        "facebook-notifications-digest",
        {
            "platform": "facebook",
            "social_account_id": social_account_id,
            "account_alias": "fb-main",
            "items": [{"actor": "Alice", "title": "commented on your post"}],
            "digest_text": "Alice: commented on your post [1m]",
        },
            artifact_type="notification_digest",
            tenant_id="tenant-a",
        )
    proof_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/proof-artifacts",
        headers=_headers(),
        json={
            "artifact_type": "registration_proof",
            "label": "fb-main-registration",
            "handle": "@fb-main",
            "url": "https://example.invalid/fb-main",
            "note": "registration proof for overview readiness",
        },
    )
    assert proof_response.status_code == 200

    overview = test_client.get(
        f"/api/v1/keystore/accounts/{social_account_id}/overview",
        headers=_headers(),
    )
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["item"]["account_alias"] == "fb-main"
    assert payload["latest_browser_session"]["browser_session_id"] == session_id
    assert payload["readiness"]["ready"] is True
    assert payload["readiness"]["blocking"] == []
    assert payload["latest_notification_digest"]["digest_text"] == "Alice: commented on your post [1m]"


def test_account_overview_prefers_explicit_session_binding_over_entity_scope_guess(client):
    test_client, db_path = client

    create_a = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main-a",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    create_b = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main-b",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    account_a = create_a.json()["item"]["social_account_id"]
    account_b = create_b.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    for social_account_id in (account_a, account_b):
        test_client.post(
            f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
            headers=_headers(),
            json={"secret_kind": "login", "alias_id": "alias-login"},
        )

    session_a = test_client.post(
        f"/api/v1/keystore/accounts/{account_a}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    ).json()["browser_session_id"]

    session_b = test_client.post(
        f"/api/v1/keystore/accounts/{account_b}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    ).json()["browser_session_id"]

    overview_a = test_client.get(
        f"/api/v1/keystore/accounts/{account_a}/overview",
        headers=_headers(),
    )
    overview_b = test_client.get(
        f"/api/v1/keystore/accounts/{account_b}/overview",
        headers=_headers(),
    )
    assert overview_a.status_code == 200
    assert overview_b.status_code == 200
    assert overview_a.json()["latest_browser_session"]["browser_session_id"] == session_a
    assert overview_b.json()["latest_browser_session"]["browser_session_id"] == session_b


def test_account_overview_surfaces_degraded_browser_session_health_when_profile_dir_missing(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )

    session_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    session_id = session_response.json()["browser_session_id"]

    profile_artifact_path = None
    with get_connection(_get_db_path()) as conn:
        row = conn.execute(
            """SELECT proof_id, path
               FROM proof_artifacts
               WHERE related_kind = 'browser_session' AND related_id = ? AND artifact_type = 'profile_dir'
               ORDER BY created_at DESC, proof_id DESC
               LIMIT 1""",
            (session_id,),
        ).fetchone()
        proof_id = row[0] if row else None
        profile_artifact_path = row[1] if row else None

    assert profile_artifact_path
    broken_profile_path = str(Path(profile_artifact_path).parent / "missing-profile-dir")
    with get_connection(_get_db_path()) as conn:
        conn.execute(
            "UPDATE proof_artifacts SET path = ? WHERE proof_id = ?",
            (broken_profile_path, proof_id),
        )

    overview = test_client.get(
        f"/api/v1/keystore/accounts/{social_account_id}/overview",
        headers=_headers(),
    )
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["latest_browser_session"]["browser_session_id"] == session_id
    assert payload["latest_browser_session_health"]["status"] == "degraded"
    assert "missing_profile_dir" in payload["latest_browser_session_health"]["issues"]
    assert payload["latest_browser_session_health"]["profile_dir_exists"] is False
    assert payload["continuity_injury_summary"]["status"] == "active"
    assert payload["continuity_injury_summary"]["active"] is True


def test_start_login_session_does_not_reuse_degraded_bound_session(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )

    first = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    first_session_id = first.json()["browser_session_id"]

    with get_connection(_get_db_path()) as conn:
        row = conn.execute(
            """SELECT proof_id, path
               FROM proof_artifacts
               WHERE related_kind = 'browser_session' AND related_id = ? AND artifact_type = 'profile_dir'
               ORDER BY created_at DESC, proof_id DESC
               LIMIT 1""",
            (first_session_id,),
        ).fetchone()
        proof_id = row[0] if row else None
        profile_artifact_path = row[1] if row else None
        assert proof_id
        assert profile_artifact_path
        conn.execute(
            "UPDATE proof_artifacts SET path = ? WHERE proof_id = ?",
            (str(Path(profile_artifact_path).parent / "missing-profile-dir"), proof_id),
        )

    second = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/start-login-session",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    second_session_id = second_payload["browser_session_id"]
    assert second_session_id != first_session_id
    assert second_payload["replaced_degraded_session"]["browser_session_id"] == first_session_id
    assert second_payload["replaced_degraded_session"]["reason"] == "missing_restart_critical_browser_artifacts"
    assert "missing_profile_dir" in second_payload["replaced_degraded_session"]["previous_health"]["issues"]

    with get_connection(_get_db_path()) as conn:
        degraded_row = conn.execute(
            "SELECT state FROM browser_sessions WHERE browser_session_id = ? AND tenant_id = ?",
            (first_session_id, "tenant-a"),
        ).fetchone()
        degraded_artifact = conn.execute(
            """SELECT artifact_type, path
               FROM proof_artifacts
               WHERE related_kind = 'browser_session' AND related_id = ? AND artifact_type = 'session_degraded'
               ORDER BY created_at DESC, proof_id DESC
               LIMIT 1""",
            (first_session_id,),
        ).fetchone()
    assert degraded_row[0] == "degraded"
    assert degraded_artifact[0] == "session_degraded"
    assert degraded_artifact[1] == "missing_restart_critical_browser_artifacts"


def test_record_account_proof_artifact_persists_and_surfaces_in_overview(client):
    test_client, _db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "fourclaw",
            "account_alias": "bayman-fourclaw",
            "entity_scope": "newfoundland-bayman",
            "persona_scope": "newfoundland_bayman_operational",
            "state": "pending",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    proof_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/proof-artifacts",
        headers=_headers(),
        json={
            "artifact_type": "registration_proof",
            "label": "moltbook-registration-01",
            "handle": "@bayman",
            "url": "https://example.invalid/bayman",
            "note": "Manual registration completed",
            "payload": {"platform_handle": "@bayman"},
            "state": "verified",
        },
    )
    assert proof_response.status_code == 200
    proof_payload = proof_response.json()
    assert proof_payload["item"]["state"] == "verified"
    assert proof_payload["artifact"]["artifact_type"] == "registration_proof"
    assert proof_payload["payload"]["handle"] == "@bayman"
    assert proof_payload["payload"]["url"] == "https://example.invalid/bayman"

    overview = test_client.get(
        f"/api/v1/keystore/accounts/{social_account_id}/overview",
        headers=_headers(),
    )
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["latest_registration_proof"]["handle"] == "@bayman"
    assert payload["latest_registration_proof"]["url"] == "https://example.invalid/bayman"
    assert payload["account_artifacts"][0]["artifact_type"] == "registration_proof"
    assert payload["proof_summary"]["latest_artifact_type"] == "registration_proof"
    assert payload["proof_summary"]["latest_handle"] == "@bayman"


def test_verify_login_surfaces_automatic_verification_proof_in_overview(client):
    test_client, db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "facebook",
            "account_alias": "fb-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(db_path),
    )
    test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/attach-secret",
        headers=_headers(),
        json={"secret_kind": "login", "alias_id": "alias-login"},
    )

    verify_response = test_client.post(
        f"/api/v1/keystore/accounts/{social_account_id}/verify-login",
        headers=_headers(),
        json={"entity_id": "entity-1"},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["artifact"]["artifact_type"] == "verification_proof"

    overview = test_client.get(
        f"/api/v1/keystore/accounts/{social_account_id}/overview",
        headers=_headers(),
    )
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["latest_registration_proof"]["state"] == "verified"
    assert payload["latest_registration_proof"]["login_secret_present"] is True
    assert payload["account_artifacts"][0]["artifact_type"] == "verification_proof"
    assert payload["latest_verification_proof"]["state"] == "verified"
    assert payload["latest_verification_proof"]["artifact_type"] == "verification_proof"
    assert payload["readiness"]["ready"] is True
    assert payload["readiness"]["blocking"] == []


def test_account_overview_surfaces_latest_post_reply_and_challenge_proofs(client):
    test_client, _db_path = client

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "moltbook",
            "account_alias": "molt-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    for artifact_type, label, payload in [
        ("post_proof", "post-01", {"url": "https://example.invalid/post/1", "title": "hello post"}),
        ("reply_proof", "reply-01", {"url": "https://example.invalid/post/1#reply-2", "thread_id": "thread-1"}),
        ("challenge_proof", "challenge-01", {"url": "https://example.invalid/challenge/3", "state": "needs_verification"}),
    ]:
        response = test_client.post(
            f"/api/v1/keystore/accounts/{social_account_id}/proof-artifacts",
            headers=_headers(),
            json={
                "artifact_type": artifact_type,
                "label": label,
                "payload": payload,
            },
        )
        assert response.status_code == 200

    overview = test_client.get(
        f"/api/v1/keystore/accounts/{social_account_id}/overview",
        headers=_headers(),
    )
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["latest_post_proof"]["url"] == "https://example.invalid/post/1"
    assert payload["latest_post_proof"]["artifact_type"] == "post_proof"
    assert payload["latest_reply_proof"]["thread_id"] == "thread-1"
    assert payload["latest_reply_proof"]["artifact_type"] == "reply_proof"
    assert payload["latest_challenge_proof"]["state"] == "needs_verification"
    assert payload["latest_challenge_proof"]["artifact_type"] == "challenge_proof"


def test_account_overview_surfaces_recent_human_notifications(client, monkeypatch):
    test_client, _db_path = client
    root = Path(".pytest-tmp-keystore-api") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HG_WORKSPACE", str(root))
    monkeypatch.setattr("app.api.keystore_entity.get_workspace_root", lambda: root)

    create_response = test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "moltbook",
            "account_alias": "moltbook-main",
            "entity_scope": "entity-1",
            "state": "active",
        },
    )
    social_account_id = create_response.json()["item"]["social_account_id"]

    record_human_notification(
        root,
        task_name="moltbook-engage",
        kind="run_update",
        message="posted a reply",
        summary={"execution": {"status": "completed", "platform": "moltbook"}},
        transport="configured_channel",
        social_account_id=social_account_id,
        tenant_id="tenant-a",
    )
    record_human_notification(
        root,
        task_name="fourclaw-engage",
        kind="run_update",
        message="wrong platform",
        summary={"execution": {"status": "completed", "platform": "fourclaw"}},
        transport="configured_channel",
        social_account_id="acct-other",
        tenant_id="tenant-a",
    )

    overview = test_client.get(
        f"/api/v1/keystore/accounts/{social_account_id}/overview",
        headers=_headers(),
    )
    assert overview.status_code == 200
    payload = overview.json()
    recent = payload["recent_human_notifications"]
    assert len(recent) == 1
    assert recent[0]["task_name"] == "moltbook-engage"
    assert recent[0]["message"] == "posted a reply"
    assert payload["notification_summary"]["count"] == 1
    assert payload["notification_summary"]["latest"]["message"] == "posted a reply"
    assert payload["last_activity_summary"]["last_seen_kind"] == "notification"
    assert payload["last_activity_summary"]["last_seen_detail"] == "run_update"


def test_list_accounts_can_filter_by_entity_scope(client):
    test_client, _db_path = client

    test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "fourclaw",
            "account_alias": "bayman-fourclaw",
            "entity_scope": "newfoundland-bayman",
            "persona_scope": "newfoundland_bayman_operational",
            "state": "verified",
        },
    )
    test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "fourclaw",
            "account_alias": "underling-fourclaw",
            "entity_scope": "underling-chan",
            "state": "verified",
        },
    )

    response = test_client.get(
        "/api/v1/keystore/accounts?platform=fourclaw&entity_scope=newfoundland-bayman",
        headers=_headers(),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["account_alias"] == "bayman-fourclaw"


def test_resolve_task_account_endpoint_returns_assigned_binding(client):
    test_client, _db_path = client

    test_client.post(
        "/api/v1/keystore/accounts",
        headers=_headers(),
        json={
            "platform": "fourclaw",
            "account_alias": "bayman-fourclaw",
            "entity_scope": "newfoundland-bayman",
            "persona_scope": "newfoundland_bayman_operational",
            "state": "verified",
        },
    )

    response = test_client.get(
        "/api/v1/keystore/accounts/resolve-task/newfoundland-bayman-fourclaw-engage",
        headers=_headers(),
    )
    assert response.status_code == 200
    item = response.json()["item"]
    assert item["account_alias"] == "bayman-fourclaw"
    assert item["entity_scope"] == "newfoundland-bayman"
