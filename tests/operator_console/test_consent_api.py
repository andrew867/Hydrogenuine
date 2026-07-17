from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app as gateway_app
from operator_console.server.app.main import app as operator_app


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture
def consent_workspace(tmp_path, monkeypatch):
    fixtures_src = Path(__file__).resolve().parents[2] / "evals" / "g15" / "consent_surface" / "fixtures.json"
    dest = tmp_path / "evals" / "g15" / "consent_surface"
    dest.mkdir(parents=True)
    shutil.copy(fixtures_src, dest / "fixtures.json")
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_CONSENT_SURFACE_ENABLED", "1")
    monkeypatch.setenv("HG_GATEWAY_DEV", "1")
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "test-api-key")
    return tmp_path


def test_grant_requires_api_key_and_writes_ledger(operator_client, consent_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    res = operator_client.post(
        "/api/v1/consent/grant",
        headers=headers,
        json={
            "subject_id": "user-1",
            "consent_class": "session",
            "purpose": "panel",
            "granted_by": "operator",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["record"]["event"] == "CONSENT_GRANTED"
    ledger_path = consent_workspace / "memory" / "governance" / "consent_ledger.jsonl"
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(r["event"] == "CONSENT_GRANTED" and r["subject_id"] == "user-1" for r in rows)


def test_revoke_updates_status_same_cycle(operator_client, consent_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    grant = operator_client.post(
        "/api/v1/consent/grant",
        headers=headers,
        json={
            "subject_id": "user-2",
            "consent_class": "workspace",
            "purpose": "audit",
            "granted_by": "operator",
        },
    ).json()
    record_id = grant["record"]["record_id"]
    revoke = operator_client.post(
        "/api/v1/consent/revoke",
        headers=headers,
        json={"record_id": record_id, "subject_id": "user-2", "revoked_by": "operator"},
    )
    assert revoke.status_code == 200
    status = revoke.json()["status"]
    assert status["effective_class"] == "none"
    assert status["active_grants"] == []
    live = operator_client.get("/api/v1/consent/status?subject_id=user-2", headers=headers)
    assert live.json()["effective_class"] == "none"


def test_gateway_recognition_probe_denies_without_consent(gateway_client, consent_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    denied = gateway_client.get("/v1/recognition/probe?subject_id=user-3", headers=headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "consent_required"
    ledger_path = consent_workspace / "memory" / "governance" / "consent_ledger.jsonl"
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(r["event"] == "CONSENT_DENIED_REQUEST" for r in rows)


def test_ledger_pages_without_mutation(operator_client, consent_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    grant = operator_client.post(
        "/api/v1/consent/grant",
        headers=headers,
        json={
            "subject_id": "user-4",
            "consent_class": "session",
            "purpose": "page",
            "granted_by": "operator",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    ).json()
    record_id = grant["record"]["record_id"]
    operator_client.post(
        "/api/v1/consent/revoke",
        headers=headers,
        json={"record_id": record_id, "subject_id": "user-4", "revoked_by": "operator"},
    )
    page = operator_client.get("/api/v1/consent/ledger?offset=0&limit=50", headers=headers).json()
    granted = [e for e in page["events"] if e.get("event") == "CONSENT_GRANTED" and e.get("record_id") == record_id]
    assert granted and granted[0].get("revoked_at") is None
    assert any(e.get("event") == "CONSENT_REVOKED" and e.get("record_id") == record_id for e in page["events"])
