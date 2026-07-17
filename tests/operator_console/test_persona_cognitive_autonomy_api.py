import os
import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    TestClient = None
    app = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    from hg_gateway import store as store_module

    store_module._store = None
    try:
        yield TestClient(app)
    finally:
        store_module._store = None


def _seed_turns():
    from hg_gateway.store import get_store

    store = get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "auto-1",
            "chat_id": "chat-1",
            "message_id": "msg-1",
            "fingerprint_id": "ada_lovelace",
            "swarm_run_id": "swarm-1",
            "swarm_role": "orchestrator",
            "arc_state": "building",
            "engagement_mode": "direct",
            "depth_level": "middle",
            "uncertainty_level": "confident",
            "callback_surface": False,
            "proactive_notice": False,
            "lateral_mode": "aside",
            "position_evolution": False,
            "relationship_type": "respect",
            "counterpart_fingerprint_id": "nikola_tesla",
            "details": {"moves": ["callback:systems"]},
            "created_at": "2026-03-08T12:00:00Z",
        },
    )
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "auto-2",
            "chat_id": "chat-2",
            "message_id": "msg-2",
            "fingerprint_id": "nikola_tesla",
            "swarm_run_id": "swarm-1",
            "swarm_role": "entity",
            "arc_state": "tension",
            "engagement_mode": "challenge",
            "depth_level": "middle",
            "uncertainty_level": "uncertain",
            "callback_surface": True,
            "proactive_notice": True,
            "lateral_mode": "skip",
            "position_evolution": True,
            "relationship_type": "respect",
            "counterpart_fingerprint_id": "ada_lovelace",
            "details": {"moves": ["position_evolution:systems"]},
            "created_at": "2026-03-08T12:05:00Z",
        },
    )


def test_persona_autonomy_history_returns_rows(client):
    _seed_turns()

    response = client.get("/api/v1/personas/autonomy/history?fingerprint_id=ada_lovelace", headers=_headers())

    assert response.status_code == 200, response.text
    history = response.json()["history"]
    assert history["count"] == 1
    assert history["items"][0]["arc_state"] == "building"


def test_persona_autonomy_summary_aggregates(client):
    _seed_turns()

    response = client.get("/api/v1/personas/autonomy/summary?hours=240", headers=_headers())

    assert response.status_code == 200, response.text
    summary = response.json()["summary"]
    assert summary["total_turns"] == 2
    assert summary["relationship_distribution"]["respect"] == 2
    assert summary["engagement_distribution"]["challenge"] == 1


def test_persona_autonomy_swarm_summary_breaks_down_members(client):
    _seed_turns()

    response = client.get("/api/v1/personas/autonomy/swarms/swarm-1?hours=240", headers=_headers())

    assert response.status_code == 200, response.text
    swarm = response.json()["swarm"]
    assert swarm["summary"]["total_turns"] == 2
    assert swarm["orchestrator"]["chat_id"] == "chat-1"
    assert len(swarm["members"]) == 1
    assert swarm["members"][0]["relationship_types"]["respect"] == 1
