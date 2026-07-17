import os
import time

import pytest

from hg_realtime.leases.store import default_lease_store


def test_default_lease_store_uses_gateway_store_with_sqlite_backend(tmp_path):
    db_path = tmp_path / "gateway.sqlite3"
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_db = os.environ.get("HG_GATEWAY_DB_PATH")
    try:
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = str(db_path)
        store = default_lease_store()
        lease = store.acquire(run_id="run-lease-1", worker_id="worker-a", stale_after_s=0.1)
        store.heartbeat(run_id="run-lease-1", lease_id=lease.lease_id, worker_id="worker-a", seq=1)
        assert store.get(run_id="run-lease-1") is not None
        with pytest.raises(RuntimeError):
            store.acquire(run_id="run-lease-1", worker_id="worker-b", stale_after_s=10.0)
        time.sleep(0.12)
        lease2 = store.acquire(run_id="run-lease-1", worker_id="worker-b", stale_after_s=0.1)
        assert lease2.worker_id == "worker-b"
        assert store.release("run-lease-1") is True
        assert store.get(run_id="run-lease-1") is None
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_db is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_db
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
