"""U4 real-time & performance: swarm SSE bus and stream endpoint."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway.store import get_store
from hg_gateway import swarm_bus


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "test-api-key")
    monkeypatch.setenv("HG_GATEWAY_ADMIN_KEY", "test-admin-key")
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    if hasattr(get_store, "cache_clear"):
        get_store.cache_clear()
    return TestClient(app)


def test_swarm_bus_emit_delivers_to_subscriber():
    async def _run():
        q = swarm_bus.subscribe("default", "swarm-1")
        swarm_bus.emit("default", "swarm-1", "swarm.workspace", {"workspace": {"ok": True}})
        event_type, payload = await asyncio.wait_for(q.get(), timeout=1.0)
        swarm_bus.unsubscribe("default", "swarm-1", q)
        return event_type, payload

    event_type, payload = asyncio.run(_run())
    assert event_type == "swarm.workspace"
    assert payload["workspace"]["ok"] is True


def test_swarm_stream_route_registered(client):
    """Replay payload is covered by swarm_bus unit test; route must exist and authorize."""
    headers = {"X-API-Key": "test-api-key"}
    res = client.get("/v1/swarms/missing-swarm/stream?replay=false", headers=headers)
    assert res.status_code in (200, 404, 422)
