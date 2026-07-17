from __future__ import annotations

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def _create_reflection(client: TestClient, artifact_id: str, title: str) -> dict:
    resp = client.post(
        "/api/v1/reflections",
        json={
            "artifact_id": artifact_id,
            "title": title,
            "summary": f"{title} summary",
            "findings_json": {"summary": f"{title} summary"},
            "source_event_ids": ["evt-1"],
            "source_memory_ids": ["mem-1"],
            "source_links": [{"kind": "run", "href": "#/runs/run-social-1", "label": "run-social-1"}],
            "confidence": 0.75,
            "verification_status": "provisional",
            "reviewed_by": "operator",
        },
    )
    assert resp.status_code == 200
    return resp.json()["artifact"]


def test_reflection_artifacts_api_inventory_and_create(monkeypatch, tmp_path) -> None:
    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        created = _create_reflection(client, "reflection:entity:phase4:001", "Operator phase 4 reflection")
        assert created["class_key"] == "reflection"
        assert created["latest_status"] == "provisional"

        list_resp = client.get("/api/v1/reflections")
        assert list_resp.status_code == 200
        artifacts = list_resp.json()["artifacts"]
        assert len(artifacts) == 1
        assert artifacts[0]["artifact_id"] == "reflection:entity:phase4:001"

        detail_resp = client.get("/api/v1/reflections/reflection:entity:phase4:001")
        assert detail_resp.status_code == 200
        artifact = detail_resp.json()["artifact"]
        assert artifact["payload_json"]
        assert artifact["versions"][0]["state"] == "provisional"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_reflection_artifacts_api_review_actions_are_audited(monkeypatch, tmp_path) -> None:
    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "default")

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        _create_reflection(client, "reflection:entity:phase4:promote", "Promote reflection")
        _create_reflection(client, "reflection:entity:phase4:discard", "Discard reflection")
        _create_reflection(client, "reflection:entity:phase4:escalate", "Escalate reflection")

        promote_resp = client.post("/api/v1/reflections/reflection:entity:phase4:promote/promote", json={"reviewed_by": "operator", "note": "looks good"})
        assert promote_resp.status_code == 200
        promoted = promote_resp.json()["artifact"]
        assert promoted["latest_status"] == "promoted"
        assert promoted["versions"][0]["state"] == "promoted"
        assert promoted["payload_json"]
        assert len(promoted["versions"]) == 2
        assert promoted["versions"][0]["change_summary"].startswith("promoted reflection artifact")
        assert "run-social-1" in promoted["payload_json"]

        discard_resp = client.post("/api/v1/reflections/reflection:entity:phase4:discard/discard", json={"reviewed_by": "operator", "note": "not needed"})
        assert discard_resp.status_code == 200
        discarded = discard_resp.json()["artifact"]
        assert discarded["latest_status"] == "discarded"
        assert discarded["versions"][0]["state"] == "discarded"
        assert len(discarded["versions"]) == 2

        escalate_resp = client.post("/api/v1/reflections/reflection:entity:phase4:escalate/escalate", json={"reviewed_by": "operator", "note": "needs human follow-up"})
        assert escalate_resp.status_code == 200
        escalated = escalate_resp.json()["artifact"]
        assert escalated["latest_status"] == "escalated"
        assert escalated["versions"][0]["state"] == "escalated"
        assert len(escalated["versions"]) == 2

        detail_resp = client.get("/api/v1/reflections/reflection:entity:phase4:promote")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()["artifact"]
        assert detail["versions"][0]["change_summary"].startswith("promoted reflection artifact")
        assert detail["versions"][0]["payload_json"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)
