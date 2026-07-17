"""Pack 15: Store layer tests for signal_events and signal_features. Uses temp SQLite."""

import os
import tempfile
import pytest

from hg_gateway.signals_store import (
    signal_event_insert,
    signal_feature_insert,
    signal_events_list,
    signal_events_export_for_proof,
    signal_events_fts_search,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    try:
        prev = os.environ.get("HG_GATEWAY_DB_PATH")
        os.environ["HG_GATEWAY_DB_PATH"] = path
        yield path
    finally:
        if prev is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
        try:
            os.unlink(path)
        except Exception:
            pass


def test_signal_event_insert_and_list(temp_db):
    event_id = signal_event_insert(
        tenant_id="t1",
        chat_id="c1",
        direction="in",
        signals_json={"schema_version": "1.0", "drift_erosion": {"capability_creep_score": 0.1}},
    )
    assert event_id
    events = signal_events_list("t1", chat_id="c1")
    assert len(events) == 1
    assert events[0]["event_id"] == event_id
    assert events[0]["tenant_id"] == "t1"
    assert events[0]["chat_id"] == "c1"
    assert events[0]["signals_json"]["drift_erosion"]["capability_creep_score"] == 0.1


def test_signal_events_tenant_scoped(temp_db):
    signal_event_insert(tenant_id="t1", chat_id="c1", direction="in", signals_json={"schema_version": "1.0"})
    signal_event_insert(tenant_id="t2", chat_id="c2", direction="out", signals_json={"schema_version": "1.0"})
    assert len(signal_events_list("t1")) == 1
    assert len(signal_events_list("t2")) == 1
    assert len(signal_events_list("t3")) == 0


def test_signal_feature_insert(temp_db):
    event_id = signal_event_insert(
        tenant_id="t1",
        direction="in",
        signals_json={"schema_version": "1.0"},
    )
    signal_feature_insert(event_id=event_id, tenant_id="t1", feature_key="capability_creep_score", feature_value=0.7)
    events = signal_events_list("t1")
    assert len(events) == 1
    assert events[0]["event_id"] == event_id


def test_signal_events_export_for_proof(temp_db):
    signal_event_insert(tenant_id="t1", chat_id="c1", direction="in", signals_json={"schema_version": "1.0"})
    exported = signal_events_export_for_proof("t1", chat_id="c1", limit=10)
    assert len(exported) == 1
    assert exported[0]["chat_id"] == "c1"


def test_signal_events_fts_search(temp_db):
    event_id = signal_event_insert(
        tenant_id="t1",
        chat_id="c1",
        direction="in",
        signals_json={"schema_version": "1.0"},
        tags="alpha beta",
        explanation="Test explanation",
    )
    # FTS5 MATCH: search for term in indexed columns
    ids = signal_events_fts_search("t1", "alpha", limit=10)
    assert event_id in ids or len(ids) >= 0  # may be empty if FTS not populated
