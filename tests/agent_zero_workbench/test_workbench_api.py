"""Workbench API + library (mission cases 1-19) — fixture-JWKS + TestClient."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.agent_zero_workbench.conftest import CLIENT_ID, mint


@pytest.fixture()
def client(monkeypatch, tmp_path, jwks_file):
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    monkeypatch.setenv("HG_OPERATOR_AUTH_MODE", "keycloak")
    monkeypatch.setenv("HG_OIDC_JWKS_FILE", jwks_file)
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8180")
    monkeypatch.setenv("KEYCLOAK_REALM", "hg")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("HG_WORKBENCH_DIR", str(tmp_path / "wb"))
    import hg_gateway.workbench_routes as wr
    wr._STORE = None  # reset the module-level store for this tmp dir
    from hg_gateway.main import app
    return TestClient(app), tmp_path / "wb"


def _b(tok):
    return {"Authorization": f"Bearer {tok}"}


def _run(c, tok, **body):
    body.setdefault("request_text", "analyze the uploaded contract")
    return c.post("/v1/workbench/runs", headers=_b(tok), json=body)


# ---- run creation (cases 1-6) ----

def test_authenticated_operator_creates_run(client, rsa_keys):
    c, _ = client
    sub = "11111111-2222-3333-4444-555555555555"
    r = _run(c, mint(rsa_keys, roles=("operator",), sub=sub))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["run_id"].startswith("wbr-")
    assert body["operator_subject"] == sub
    assert body["external_effects_enabled"] is False
    assert body["status"] == "created"


def test_unauthenticated_create_rejected(client):
    c, sink = client
    r = c.post("/v1/workbench/runs", json={"request_text": "x"})
    assert r.status_code == 401
    assert not (sink.exists() and any(sink.iterdir()))


def test_service_role_rejected(client, rsa_keys):
    c, _ = client
    r = _run(c, mint(rsa_keys, roles=("service", "operator")))
    assert r.status_code == 403


def test_run_ids_isolated_across_operators(client, rsa_keys):
    c, _ = client
    tok_a = mint(rsa_keys, roles=("operator",), sub="op-aaaa-1111")
    tok_b = mint(rsa_keys, roles=("operator",), sub="op-bbbb-2222")
    run_a = _run(c, tok_a).json()["run_id"]
    # operator B cannot read operator A's run
    assert c.get(f"/v1/workbench/runs/{run_a}", headers=_b(tok_b)).status_code == 403
    # and B's list does not include A's run
    b_list = c.get("/v1/workbench/runs", headers=_b(tok_b)).json()["runs"]
    assert all(r["run_id"] != run_a for r in b_list)


def test_run_detail_returns_receipt_timeline(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-tl-1")
    run_id = _run(c, tok).json()["run_id"]
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline", headers=_b(tok)).json()
    assert tl["chain"]["ok"] is True
    assert tl["receipts"][0]["kind"] == "run_created"


def test_external_effects_false_by_default(client, rsa_keys):
    c, _ = client
    run = _run(c, mint(rsa_keys, roles=("operator",), sub="op-ext-1")).json()
    assert run["external_effects_enabled"] is False


# ---- artifacts (cases 7-10) ----

def test_artifact_attaches_and_isolates(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-art-1")
    other = mint(rsa_keys, roles=("operator",), sub="op-art-2")
    run_id = _run(c, tok).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/artifacts", headers=_b(tok),
               json={"filename": "contract.pdf", "mime_type": "application/pdf",
                     "size_bytes": 2048, "content_hash": "sha256:" + "c" * 64})
    assert r.status_code == 200, r.text
    art = r.json()
    assert art["run_id"] == run_id
    # cross-run/operator artifact registration blocked
    r2 = c.post(f"/v1/workbench/runs/{run_id}/artifacts", headers=_b(other),
                json={"filename": "x", "content_hash": "sha256:" + "d" * 64})
    assert r2.status_code == 403


def test_artifact_receipt_and_no_raw_content(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-art-3")
    run_id = _run(c, tok).json()["run_id"]
    c.post(f"/v1/workbench/runs/{run_id}/artifacts", headers=_b(tok),
           json={"filename": "secret.txt", "content_hash": "sha256:" + "e" * 64})
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline", headers=_b(tok)).json()
    art = [r for r in tl["receipts"] if r["kind"] == "artifact_registered"][0]
    # receipt carries the content HASH, not raw content or filename body
    assert art["content_hash"].startswith("sha256:")
    assert "eyJ" not in json.dumps(tl)


# ---- progress / subagents / persona (cases 11-14) ----

def test_progress_and_subagent_lane(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-prog-1")
    run_id = _run(c, tok).json()["run_id"]
    ev = c.post(f"/v1/workbench/runs/{run_id}/progress", headers=_b(tok),
                json={"event_type": "subagent_started", "subagent_lane_id": "lane-1",
                      "persona": "researcher"}).json()
    assert ev["authority"] is False
    run = c.get(f"/v1/workbench/runs/{run_id}", headers=_b(tok)).json()
    assert "lane-1" in run["subagent_lane_ids"]
    assert run["status"] == "in_progress"


def test_persona_selected_recorded(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-persona-1")
    run_id = _run(c, tok).json()["run_id"]
    c.post(f"/v1/workbench/runs/{run_id}/progress", headers=_b(tok),
           json={"event_type": "persona_selected", "persona": "critic",
                 "subagent_lane_id": "lane-x"})
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline", headers=_b(tok)).json()
    ev = [r for r in tl["receipts"] if r.get("event_type") == "persona_selected"][0]
    assert ev["authority"] is False


def test_progress_event_cannot_authorize(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-auth-1")
    run_id = _run(c, tok).json()["run_id"]
    ev = c.post(f"/v1/workbench/runs/{run_id}/progress", headers=_b(tok),
                json={"event_type": "approval_required"}).json()
    # a progress event carries no authorization capability, only authority:false
    assert ev["authority"] is False
    assert "permit" not in ev and "capability" not in ev and "token" not in ev


def test_unknown_event_type_rejected(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-evt-1")
    run_id = _run(c, tok).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/progress", headers=_b(tok),
               json={"event_type": "definitely_not_a_type"})
    assert r.status_code == 400


# ---- steering / settings (cases 15-19) ----

def test_steering_receipted(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-steer-1")
    run_id = _run(c, tok).json()["run_id"]
    msg = c.post(f"/v1/workbench/runs/{run_id}/steering", headers=_b(tok),
                 json={"text": "focus on liability clauses"}).json()
    assert msg["authority"] == "advice_not_authority"
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline", headers=_b(tok)).json()
    assert any(r["kind"] == "steering_message" for r in tl["receipts"])


def test_low_risk_setting_receipted(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-set-1")
    run_id = _run(c, tok).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/settings", headers=_b(tok),
               json={"setting": "note", "action_class": "draft",
                     "old_value": "", "new_value": "hi"})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] is True


def test_high_risk_setting_held_without_stepup(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator", "hg.model_operator"), sub="op-set-2")
    run_id = _run(c, tok).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/settings", headers=_b(tok),
               json={"setting": "model_route", "action_class": "model_route_change",
                     "old_value": "a", "new_value": "b"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "setting_change_held"
    # a held change is still receipted (evidence)
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline", headers=_b(tok)).json()
    sc = [r for r in tl["receipts"] if r["kind"] == "setting_change"][0]
    assert sc["applied"] is False


def test_model_route_and_persona_change_recorded(client, rsa_keys):
    c, _ = client
    # admin + fresh step-up can apply model_route_change
    tok = mint(rsa_keys, roles=("operator", "hg.admin", "hg.model_operator"),
               sub="op-set-3", amr=("pwd", "otp"))
    run_id = _run(c, tok).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/settings", headers=_b(tok),
               json={"setting": "model_route", "action_class": "model_route_change",
                     "old_value": "gpt", "new_value": "claude"})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] is True
    # persona change (draft, run-scoped) recorded
    r2 = c.post(f"/v1/workbench/runs/{run_id}/settings", headers=_b(tok),
                json={"setting": "persona", "action_class": "draft",
                      "old_value": "researcher", "new_value": "critic"})
    assert r2.status_code == 200 and r2.json()["applied"] is True


def test_unauthenticated_setting_change_rejected(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-set-4")
    run_id = _run(c, tok).json()["run_id"]
    r = c.post(f"/v1/workbench/runs/{run_id}/settings",
               json={"setting": "x", "action_class": "draft"})
    assert r.status_code == 401


def test_full_chain_validates_end_to_end(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-chain-1")
    run_id = _run(c, tok).json()["run_id"]
    c.post(f"/v1/workbench/runs/{run_id}/artifacts", headers=_b(tok),
           json={"filename": "a", "content_hash": "sha256:" + "f" * 64})
    c.post(f"/v1/workbench/runs/{run_id}/progress", headers=_b(tok),
           json={"event_type": "model_progress"})
    c.post(f"/v1/workbench/runs/{run_id}/steering", headers=_b(tok),
           json={"text": "go"})
    tl = c.get(f"/v1/workbench/runs/{run_id}/timeline", headers=_b(tok)).json()
    assert tl["chain"]["ok"] is True
    assert tl["chain"]["count"] == 4  # run + artifact + progress + steering
