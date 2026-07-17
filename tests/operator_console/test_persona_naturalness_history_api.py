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
    store.persona_naturalness_add_turn(
        "default",
        {
            "turn_id": "turn-1",
            "chat_id": "chat-1",
            "message_id": "msg-1",
            "fingerprint_id": "ada_lovelace",
            "skin_id": "default",
            "swarm_run_id": "swarm-1",
            "swarm_role": "orchestrator",
            "input_type": "question",
            "emotional_register": "curious",
            "stress_level": "mild",
            "chosen_register": "thoughtful",
            "chosen_entry_point": "systems",
            "tic_count": 1,
            "sample_overlap_score": 0.12,
            "recent_overlap_score": 0.07,
            "regeneration_attempted": True,
            "regeneration_succeeded": True,
            "created_at": "2026-03-08T12:00:00Z",
            "issues": [{"issue_code": "repeat.opening", "payload": {"score": 0.8}}],
        },
    )
    store.persona_naturalness_add_turn(
        "default",
        {
            "turn_id": "turn-2",
            "chat_id": "chat-2",
            "message_id": "msg-2",
            "fingerprint_id": "nikola_tesla",
            "swarm_run_id": "swarm-1",
            "swarm_role": "entity",
            "input_type": "challenge",
            "emotional_register": "skeptical",
            "stress_level": "moderate",
            "chosen_register": "sharp",
            "chosen_entry_point": "counter",
            "tic_count": 0,
            "sample_overlap_score": 0.22,
            "recent_overlap_score": 0.15,
            "regeneration_attempted": False,
            "regeneration_succeeded": False,
            "created_at": "2026-03-08T12:05:00Z",
            "issues": ["repeat.argument"],
        },
    )


def test_persona_naturalness_history_returns_filtered_rows(client):
    _seed_turns()

    response = client.get(
        "/api/v1/personas/naturalness/history?fingerprint_id=ada_lovelace&limit=10",
        headers=_headers(),
    )

    assert response.status_code == 200, response.text
    history = response.json()["history"]
    assert history["count"] == 1
    assert history["items"][0]["fingerprint_id"] == "ada_lovelace"
    assert history["items"][0]["issues"][0]["issue_code"] == "repeat.opening"


def test_persona_naturalness_summary_aggregates(client):
    _seed_turns()

    response = client.get("/api/v1/personas/naturalness/summary?hours=240", headers=_headers())

    assert response.status_code == 200, response.text
    summary = response.json()["summary"]
    assert summary["total_turns"] == 2
    assert summary["unique_personas"] == 2
    assert summary["top_issue_buckets"]["repeat.argument"] == 1
    assert summary["entry_point_distribution"]["systems"] == 1


def test_persona_naturalness_swarm_summary_returns_breakdown(client):
    _seed_turns()

    response = client.get("/api/v1/personas/naturalness/swarms/swarm-1?hours=240", headers=_headers())

    assert response.status_code == 200, response.text
    swarm = response.json()["swarm"]
    assert swarm["summary"]["total_turns"] == 2
    assert swarm["orchestrator"]["chat_id"] == "chat-1"
    assert len(swarm["members"]) == 1
    assert swarm["members"][0]["chat_id"] == "chat-2"


def test_persona_naturalness_history_empty_shape_is_stable(client):
    response = client.get("/api/v1/personas/naturalness/history?fingerprint_id=missing", headers=_headers())

    assert response.status_code == 200, response.text
    history = response.json()["history"]
    assert history["count"] == 0
    assert history["items"] == []
