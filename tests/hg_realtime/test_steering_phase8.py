"""Phase 8: Steering store, get_pending, check_steering (cancel writes file)."""

import gc
import os
import tempfile
import time
import uuid

import pytest

from hg_realtime.steering import (
    SteeringEvent,
    SqliteSteeringStore,
    SqliteSteeringAdapter,
    default_steering_store,
    get_pending,
    check_steering,
    set_default_store,
)


def test_steering_store_submit_and_get_pending():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "steering.sqlite")
        store = SqliteSteeringStore(db_path=db)
        evt = SteeringEvent(
            steering_id=str(uuid.uuid4()),
            tenant_id="t1",
            actor_id="a1",
            correlation_id="c1",
            run_id="run-1",
            node_id=None,
            kind="cancel",
            payload={"reason": "test"},
        )
        store.submit(evt)
        pending = store.get_pending("run-1")
        assert len(pending) == 1
        assert pending[0]["kind"] == "cancel"
        assert pending[0]["run_id"] == "run-1"
        store.mark_consumed(pending[0]["steering_id"])
        assert len(store.get_pending("run-1")) == 0
        del store
        gc.collect()
        time.sleep(0.05)


def test_get_pending_module_level():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "steering2.sqlite")
        store = SqliteSteeringStore(db_path=db)
        set_default_store(store)
        try:
            evt = SteeringEvent(
                steering_id=str(uuid.uuid4()),
                tenant_id="t1",
                actor_id="a1",
                correlation_id="c1",
                run_id="run-2",
                node_id="n1",
                kind="inject",
                payload={"instruction": "be formal"},
            )
            store.submit(evt)
            pending = get_pending("run-2")
            assert len(pending) == 1
            assert pending[0]["kind"] == "inject"
        finally:
            set_default_store(None)
            del store
            gc.collect()
            time.sleep(0.05)


def test_check_steering_cancel_writes_file():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "steering.sqlite")
        run_dir = os.path.join(td, "run_dir")
        os.makedirs(run_dir, exist_ok=True)
        store = SqliteSteeringStore(db_path=db)
        evt = SteeringEvent(
            steering_id=str(uuid.uuid4()),
            tenant_id="t1",
            actor_id="a1",
            correlation_id="c1",
            run_id="run-cancel",
            node_id=None,
            kind="cancel",
            payload={"reason": "e2e"},
        )
        store.submit(evt)
        set_default_store(store)
        try:
            action, _ = check_steering("run-cancel", run_dir=run_dir, store=store)
            assert action == "cancel"
            cancel_file = os.path.join(run_dir, "cancel.requested.json")
            assert os.path.isfile(cancel_file)
            import json
            data = json.loads(open(cancel_file, encoding="utf-8").read())
            assert data.get("run_id") == "run-cancel"
        finally:
            set_default_store(None)
            del store
            gc.collect()
            time.sleep(0.05)


def test_sqlite_adapter_submit():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "steering_adapter.sqlite")
        adapter = SqliteSteeringAdapter(db_path=db)
        evt = SteeringEvent(
            steering_id=str(uuid.uuid4()),
            tenant_id="t1",
            actor_id="a1",
            correlation_id="c1",
            run_id="run-3",
            node_id=None,
            kind="resume",
            payload={},
        )
        adapter.submit(evt)
        pending = adapter.store.get_pending("run-3")
        assert len(pending) == 1
        assert pending[0]["kind"] == "resume"
        del adapter
        gc.collect()
        time.sleep(0.05)


def test_default_steering_store_uses_gateway_db_when_configured(tmp_path):
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_db = os.environ.get("HG_GATEWAY_DB_PATH")
    try:
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
        store = default_steering_store()
        evt = SteeringEvent(
            steering_id=str(uuid.uuid4()),
            tenant_id="t1",
            actor_id="a1",
            correlation_id="c1",
            run_id="run-gateway-steering",
            node_id=None,
            kind="inject",
            payload={"instruction": "stay sharp"},
        )
        store.submit(evt)
        pending = store.get_pending("run-gateway-steering")
        assert len(pending) == 1
        assert pending[0]["kind"] == "inject"
        store.mark_consumed(pending[0]["steering_id"])
        assert store.get_pending("run-gateway-steering") == []
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_db is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_db
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
