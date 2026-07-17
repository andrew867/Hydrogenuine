import pytest

from hg_gateway.db import get_connection
from hg_gateway.store import InMemoryStore
from hg_gateway.store_sqlite import SQLiteStore


T = "default"


@pytest.fixture
def sqlite_store(tmp_path):
    return SQLiteStore(db_path=str(tmp_path / "gateway.sqlite3"))


def _turn_payload(**overrides):
    payload = {
        "turn_id": "turn-1",
        "chat_id": "chat-1",
        "message_id": "msg-1",
        "fingerprint_id": "ada_lovelace",
        "skin_id": "default",
        "swarm_run_id": None,
        "swarm_role": None,
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
    }
    payload.update(overrides)
    return payload


def test_migration_creates_persona_naturalness_tables(tmp_path):
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "persona_naturalness_turns" in tables
    assert "persona_naturalness_issues" in tables


def test_inmemory_persona_naturalness_store_round_trip():
    store = InMemoryStore()
    store.persona_naturalness_add_turn(T, _turn_payload())

    rows = store.persona_naturalness_list(T)
    assert len(rows) == 1
    assert rows[0]["turn_id"] == "turn-1"
    assert rows[0]["issues"][0]["issue_code"] == "repeat.opening"

    summary = store.persona_naturalness_summary(T)
    assert summary["total_turns"] == 1
    assert summary["regeneration_rate"] == 1.0
    assert summary["top_issue_buckets"]["repeat.opening"] == 1


def test_sqlite_persona_naturalness_store_round_trip(sqlite_store):
    sqlite_store.persona_naturalness_add_turn(T, _turn_payload())

    rows = sqlite_store.persona_naturalness_list(T)
    assert len(rows) == 1
    assert rows[0]["message_id"] == "msg-1"
    assert rows[0]["regeneration_attempted"] is True
    assert rows[0]["issues"][0]["payload"]["score"] == 0.8


def test_sqlite_persona_naturalness_summary_aggregates(sqlite_store):
    sqlite_store.persona_naturalness_add_turn(T, _turn_payload(turn_id="turn-1", message_id="msg-1", chosen_entry_point="systems", stress_level="mild"))
    sqlite_store.persona_naturalness_add_turn(
        T,
        _turn_payload(
            turn_id="turn-2",
            message_id="msg-2",
            chat_id="chat-2",
            fingerprint_id="tesla",
            chosen_entry_point="counter",
            sample_overlap_score=0.32,
            recent_overlap_score=0.18,
            tic_count=0,
            regeneration_attempted=False,
            regeneration_succeeded=False,
            issues=["repeat.argument"],
        ),
    )

    summary = sqlite_store.persona_naturalness_summary(T)
    assert summary["total_turns"] == 2
    assert summary["unique_personas"] == 2
    assert summary["stress_distribution"]["mild"] == 2
    assert summary["entry_point_distribution"]["systems"] == 1
    assert summary["entry_point_distribution"]["counter"] == 1
    assert summary["regeneration_rate"] == 0.5
    assert summary["top_issue_buckets"]["repeat.opening"] == 1
    assert summary["top_issue_buckets"]["repeat.argument"] == 1


def test_sqlite_persona_naturalness_filters_and_limits(sqlite_store):
    sqlite_store.persona_naturalness_add_turn(T, _turn_payload(turn_id="turn-1", chat_id="chat-a", fingerprint_id="ada_lovelace", created_at="2026-03-08T10:00:00Z"))
    sqlite_store.persona_naturalness_add_turn(T, _turn_payload(turn_id="turn-2", chat_id="chat-b", fingerprint_id="tesla", created_at="2026-03-08T11:00:00Z"))
    sqlite_store.persona_naturalness_add_turn(T, _turn_payload(turn_id="turn-3", chat_id="chat-c", fingerprint_id="ada_lovelace", created_at="2026-03-08T12:00:00Z"))

    filtered = sqlite_store.persona_naturalness_list(T, fingerprint_id="ada_lovelace", limit=10)
    assert [row["turn_id"] for row in filtered] == ["turn-3", "turn-1"]

    limited = sqlite_store.persona_naturalness_list(T, limit=2)
    assert len(limited) == 2
    assert [row["turn_id"] for row in limited] == ["turn-3", "turn-2"]


def test_sqlite_persona_naturalness_swarm_summary_breaks_out_roles(sqlite_store):
    sqlite_store.persona_naturalness_add_turn(
        T,
        _turn_payload(
            turn_id="orchestrator-turn",
            chat_id="chat-parent",
            message_id="msg-parent",
            swarm_run_id="swarm-1",
            swarm_role="orchestrator",
            chosen_entry_point="direct",
        ),
    )
    sqlite_store.persona_naturalness_add_turn(
        T,
        _turn_payload(
            turn_id="member-turn",
            chat_id="chat-child",
            message_id="msg-child",
            swarm_run_id="swarm-1",
            swarm_role="entity",
            chosen_entry_point="example",
            regeneration_attempted=False,
            regeneration_succeeded=False,
        ),
    )

    summary = sqlite_store.persona_naturalness_swarm_summary(T, "swarm-1")
    assert summary["summary"]["total_turns"] == 2
    assert summary["orchestrator"]["chat_id"] == "chat-parent"
    assert len(summary["members"]) == 1
    assert summary["members"][0]["chat_id"] == "chat-child"
