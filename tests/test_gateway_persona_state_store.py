import os

from hg_gateway.store_sqlite import SQLiteStore


def test_sqlite_chat_persona_state_round_trip(tmp_path):
    db_path = tmp_path / "gateway.sqlite3"
    os.environ["HG_GATEWAY_DB_PATH"] = str(db_path)
    try:
        store = SQLiteStore(str(db_path))
        chat_id = store.chat_create("default", title="State test")
        payload = {
            "current_stress_level": "mild",
            "recent_verbal_tics": ["here's the thing"],
            "recent_entry_points": ["principle"],
            "turn_count": 2,
        }
        store.chat_set_persona_state("default", chat_id, payload)
        loaded = store.chat_get_persona_state("default", chat_id)
        assert loaded["current_stress_level"] == "mild"
        assert loaded["recent_verbal_tics"] == ["here's the thing"]
        assert loaded["turn_count"] == 2
    finally:
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
