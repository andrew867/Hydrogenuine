"""L10 event store: append_event, list_events (Phase 8)."""

import gc
import os
import tempfile
import time

import pytest


def test_append_and_list_events():
    from operator_console.server.app.services.event_store import (
        append_event,
        list_events,
        _init,
    )
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "gateway.sqlite3")
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = db
        try:
            _init()
            eid = append_event(
                tenant_id="t1",
                actor_id="a1",
                correlation_id="corr-1",
                run_id="run-1",
                payload={"kind": "test"},
            )
            assert eid
            events = list_events(correlation_id="corr-1")
            assert len(events) == 1
            assert events[0]["event_id"] == eid
            assert events[0]["run_id"] == "run-1"
            events_run = list_events(run_id="run-1")
            assert len(events_run) == 1
        finally:
            os.environ.pop("HG_GATEWAY_STORE", None)
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
            gc.collect()
            time.sleep(0.05)
