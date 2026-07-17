import os
import uuid

import pytest

# These exercise a real PostgreSQL backend (they connect to a live DSN, not just
# import psycopg), so they hang/fail without a server. Auto-skip when no Postgres
# is reachable or when hermetic (HG_CI_HERMETIC=1); see tests/conftest.py.
pytestmark = pytest.mark.requires_postgres

psycopg = pytest.importorskip("psycopg")

from hg_realtime.integrations.run_index import default_run_index_reader, default_run_index_writer
from hg_realtime.leases.store import default_lease_store


@pytest.fixture
def postgres_gateway_env():
    dsn = os.environ.get("HG_TEST_POSTGRES_DSN") or os.environ.get("HG_GATEWAY_POSTGRES_DSN") or "postgresql://hg:hg@127.0.0.1:55432/hg_demo"
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_dsn = os.environ.get("HG_GATEWAY_POSTGRES_DSN")
    os.environ["HG_GATEWAY_STORE"] = "postgres"
    os.environ["HG_GATEWAY_POSTGRES_DSN"] = dsn
    try:
        yield dsn
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_dsn is not None:
            os.environ["HG_GATEWAY_POSTGRES_DSN"] = prev_dsn
        else:
            os.environ.pop("HG_GATEWAY_POSTGRES_DSN", None)


def test_shared_run_index_on_postgres(postgres_gateway_env):
    writer = default_run_index_writer()
    reader = default_run_index_reader()
    run_id = f"pg-run-{uuid.uuid4()}"
    corr = f"pg-corr-{uuid.uuid4()}"
    writer.record_start(run_id=run_id, workflow_id="wf-pg", correlation_id=corr, run_dir=f"/tmp/{run_id}")
    row = reader.get_run(run_id)
    assert row is not None
    assert row.workflow_id == "wf-pg"
    writer.record_completion(run_id=run_id, status="completed", completed_ts=321.0)
    row2 = reader.get_run_by_correlation_id(corr)
    assert row2 is not None
    assert row2.status == "completed"


def test_shared_run_leases_on_postgres(postgres_gateway_env):
    store = default_lease_store()
    run_id = f"pg-lease-{uuid.uuid4()}"
    lease = store.acquire(run_id=run_id, worker_id="pg-worker", stale_after_s=5.0)
    store.heartbeat(run_id=run_id, lease_id=lease.lease_id, worker_id="pg-worker", seq=1)
    current = store.get(run_id=run_id)
    assert current is not None
    assert current.worker_id == "pg-worker"
    assert store.release(run_id) is True
