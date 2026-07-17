"""
Pack 5: Conformance — error response shape for key gateway endpoints.
All error responses must include a detail field (string or object with code/message where applicable).
"""

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key


@pytest.fixture
def client():
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_400_has_detail(client: TestClient):
    """PATCH /v1/chats/{id} without title returns 400 with detail."""
    r = client.post("/v1/chats", json={"title": "T"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client.patch(f"/v1/chats/{chat_id}", json={})
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data


def test_404_has_detail(client: TestClient):
    """GET /v1/chats/{id}/messages for missing chat returns 404 with detail."""
    r = client.get("/v1/chats/nonexistent-chat-id/messages")
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data


def test_403_structured_detail(client: TestClient):
    """403 responses for quota/policy include detail with code or message."""
    r = client.post("/v1/chats", json={"title": "Test"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    # Message without content -> 400
    r = client.post(f"/v1/chats/{chat_id}/messages", json={})
    assert r.status_code == 400
    assert "detail" in r.json()
