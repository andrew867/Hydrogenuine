"""
Test plan: SSE Streaming (04_streaming_protocol_sse)
- GET /v1/stream?chat_id=... and GET /v1/chats/{id}/stream return SSE
- Event types documented; replay optional
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


def test_stream_requires_chat_id(client):
    r = client.get("/v1/stream")
    assert r.status_code == 400
    assert "chat_id" in (r.json() or {}).get("detail", "")


# GET /v1/stream?chat_id=... returns 200 and streams; not asserted here (infinite stream).
# Integration: open SSE, POST message, receive deltas + final (see e2e / PROOF_SUITE).
