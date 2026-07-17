from hg_overseer.overseer_core.telegram_queue import enforce_pending_cap, normalize_pending_data


def test_normalize_pending_data_defaults_on_invalid_input():
    assert normalize_pending_data(None) == {"pending": [], "history": []}
    assert normalize_pending_data({"pending": "nope", "history": 123}) == {"pending": [], "history": []}


def test_enforce_pending_cap_drops_oldest_entries():
    data = {
        "pending": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}],
        "history": [{"id": "h1"}],
    }
    bounded, dropped = enforce_pending_cap(data, 2)
    assert dropped == 2
    assert [item["id"] for item in bounded["pending"]] == ["3", "4"]
    assert [item["id"] for item in bounded["history"]] == ["h1"]
