import os

from hg_gateway.store_sqlite import SQLiteStore


def test_sqlite_chat_persona_autonomy_state_round_trip(tmp_path):
    db_path = tmp_path / "gateway.sqlite3"
    os.environ["HG_GATEWAY_DB_PATH"] = str(db_path)
    try:
        store = SQLiteStore(str(db_path))
        chat_id = store.chat_create("default", title="Autonomy state test")
        payload = {
            "dominant_concern": "architecture",
            "turn_count": 3,
            "open_loops": [
                {
                    "id": "loop-1",
                    "topic": "architecture",
                    "summary": "Need to revisit the boundary.",
                    "turn_opened": 2,
                    "urgency": 0.8,
                    "salience": 0.7,
                    "status": "active",
                    "callback_eligible_after_turn": 4,
                }
            ],
        }
        store.chat_set_persona_autonomy_state("default", chat_id, payload)
        loaded = store.chat_get_persona_autonomy_state("default", chat_id)
        assert loaded["dominant_concern"] == "architecture"
        assert loaded["turn_count"] == 3
        assert loaded["open_loops"][0]["topic"] == "architecture"
    finally:
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
