import gc
import os
import tempfile
import time
import pytest
from hg_realtime.leases.store import RunLeaseStore

def test_acquire_and_heartbeat_and_reap():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "leases.sqlite")
        store = RunLeaseStore(db)
        lease = store.acquire(run_id="r1", worker_id="w1", stale_after_s=0.1)
        store.heartbeat(run_id="r1", lease_id=lease.lease_id, worker_id="w1", seq=1)

        with pytest.raises(RuntimeError):
            store.acquire(run_id="r1", worker_id="w2", stale_after_s=10.0)

        time.sleep(0.12)
        lease2 = store.acquire(run_id="r1", worker_id="w2", stale_after_s=0.1)
        assert lease2.worker_id == "w2"

        time.sleep(0.12)
        reaped = store.reap_stale(stale_after_s=0.1)
        assert reaped >= 1

        # On Windows, SQLite may hold the file handle briefly after last use.
        # Release store and run gc so temp dir cleanup can unlink the db file.
        del store
        gc.collect()
        time.sleep(0.05)


def test_lease_release():
    import os
    from hg_realtime.leases.store import RunLeaseStore
    fd, db = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        store = RunLeaseStore(db)
        lease = store.acquire(run_id="r1", worker_id="w1", stale_after_s=30.0)
        assert store.get(run_id="r1") is not None
        released = store.release("r1")
        assert released is True
        assert store.get(run_id="r1") is None
        released_again = store.release("r1")
        assert released_again is False
    finally:
        try:
            os.unlink(db)
        except PermissionError:
            pass
