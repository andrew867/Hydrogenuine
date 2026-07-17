import os
import uuid

import pytest

# Connects to a live PostgreSQL DSN, so it hangs/fails without a server.
# Auto-skip when no Postgres is reachable or hermetic; see tests/conftest.py.
pytestmark = pytest.mark.requires_postgres

pytest.importorskip("psycopg")

from hg_realtime.steering import SteeringEvent, default_steering_store


def test_default_steering_store_uses_postgres_when_configured():
    dsn = os.environ.get("HG_TEST_POSTGRES_DSN") or os.environ.get("HG_GATEWAY_POSTGRES_DSN") or "postgresql://hg:hg@127.0.0.1:55432/hg_demo"
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_dsn = os.environ.get("HG_GATEWAY_POSTGRES_DSN")
    try:
        os.environ["HG_GATEWAY_STORE"] = "postgres"
        os.environ["HG_GATEWAY_POSTGRES_DSN"] = dsn
        store = default_steering_store()
        run_id = f"pg-steering-{uuid.uuid4()}"
        evt = SteeringEvent(
            steering_id=str(uuid.uuid4()),
            tenant_id="t1",
            actor_id="a1",
            correlation_id="c1",
            run_id=run_id,
            node_id=None,
            kind="pause",
            payload={"note": "postgres"},
        )
        store.submit(evt)
        pending = store.get_pending(run_id)
        assert len(pending) == 1
        assert pending[0]["kind"] == "pause"
        store.mark_consumed(pending[0]["steering_id"])
        assert store.get_pending(run_id) == []
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_dsn is not None:
            os.environ["HG_GATEWAY_POSTGRES_DSN"] = prev_dsn
        else:
            os.environ.pop("HG_GATEWAY_POSTGRES_DSN", None)
