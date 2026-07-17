"""Cookie-session → Workbench: a verified browser session can drive the spine."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    monkeypatch.setenv("HG_OPERATOR_AUTH_MODE", "keycloak")
    monkeypatch.setenv("HG_WORKBENCH_DIR", str(tmp_path / "wb"))
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8180")
    monkeypatch.setenv("KEYCLOAK_REALM", "hg")
    import hg_gateway.workbench_routes as wr
    wr._STORE = None
    from hg_gateway.main import app
    from hg_gateway.auth_routes import SESSION_COOKIE_NAME, SESSION_TTL_SEC
    from hg_gateway.session_store import create_session
    return TestClient(app), SESSION_COOKIE_NAME, create_session, SESSION_TTL_SEC


def _session_cookie(create_session, ttl, *, sub, roles):
    sid, _ = create_session("default", "demo-operator", list(roles),
                            ttl_seconds=ttl, idp_sub=sub)
    return sid


def test_verified_cookie_session_creates_run(client):
    c, cookie, create_session, ttl = client
    sid = _session_cookie(create_session, ttl, sub="kc-sub-cookie-1",
                          roles=["operator"])
    c.cookies.set(cookie, sid)
    r = c.post("/v1/workbench/runs", json={"request_text": "analyze via browser"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["operator_subject"] == "kc-sub-cookie-1"
    assert body["external_effects_enabled"] is False
    # timeline reachable via the same cookie session
    tl = c.get(f"/v1/workbench/runs/{body['run_id']}/timeline")
    assert tl.status_code == 200 and tl.json()["chain"]["ok"] is True
    assert "eyJ" not in json.dumps(tl.json())


def test_cookie_without_idp_sub_rejected(client):
    c, cookie, create_session, ttl = client
    # a session with no idp_sub (e.g. an api-key/demo login) cannot operate workbench
    sid = _session_cookie(create_session, ttl, sub=None, roles=["operator"])
    c.cookies.set(cookie, sid)
    r = c.post("/v1/workbench/runs", json={"request_text": "x"})
    assert r.status_code == 401


def test_cookie_non_operator_rejected(client):
    c, cookie, create_session, ttl = client
    sid = _session_cookie(create_session, ttl, sub="kc-sub-viewer",
                          roles=["viewer"])
    c.cookies.set(cookie, sid)
    r = c.post("/v1/workbench/runs", json={"request_text": "x"})
    assert r.status_code == 403


def test_no_cookie_no_bearer_rejected(client):
    c, cookie, create_session, ttl = client
    r = c.post("/v1/workbench/runs", json={"request_text": "x"})
    assert r.status_code == 401


def test_cookie_session_high_risk_held(client):
    # cookie sessions carry no amr → high-risk setting change correctly HELD
    c, cookie, create_session, ttl = client
    sid = _session_cookie(create_session, ttl, sub="kc-sub-hr",
                          roles=["operator", "hg.model_operator"])
    c.cookies.set(cookie, sid)
    run_id = c.post("/v1/workbench/runs",
                    json={"request_text": "route"}).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/settings",
               json={"setting": "model_route", "action_class": "model_route_change",
                     "old_value": "a", "new_value": "b"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "setting_change_held"


def test_cookie_session_full_spine(client):
    c, cookie, create_session, ttl = client
    sid = _session_cookie(create_session, ttl, sub="kc-sub-spine",
                          roles=["operator"])
    c.cookies.set(cookie, sid)
    run_id = c.post("/v1/workbench/runs",
                    json={"request_text": "full spine"}).json()["run_id"]
    # artifact (browser-hash metadata), progress, steering
    assert c.post(f"/v1/workbench/runs/{run_id}/artifacts",
                  json={"filename": "c.pdf", "size_bytes": 10,
                        "content_hash": "sha256:" + "a" * 64}).status_code == 200
    assert c.post(f"/v1/workbench/runs/{run_id}/progress",
                  json={"event_type": "subagent_started",
                        "subagent_lane_id": "lane-1",
                        "persona": "researcher"}).status_code == 200
    assert c.post(f"/v1/workbench/runs/{run_id}/steering",
                  json={"text": "focus on 3"}).status_code == 200
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline").json()
    kinds = [r["kind"] for r in tl["receipts"]]
    assert kinds == ["run_created", "artifact_registered", "progress_event",
                     "steering_message"]
    assert tl["chain"]["ok"] is True


def test_artifact_rejects_bad_content_hash(client):
    c, cookie, create_session, ttl = client
    sid = _session_cookie(create_session, ttl, sub="kc-sub-hash",
                          roles=["operator"])
    c.cookies.set(cookie, sid)
    run_id = c.post("/v1/workbench/runs",
                    json={"request_text": "x"}).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/artifacts",
               json={"filename": "x", "content_hash": "not-a-hash"})
    assert r.status_code == 400
