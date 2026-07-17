"""Cancel run: release lease and stop process."""

import os
import subprocess
import sys
import tempfile
import threading

import pytest

from hg_realtime.integrations.cancel import cancel_run
from hg_realtime.integrations.run_tracker import TrackedRun, get_default_tracker, _heartbeat_loop
from hg_realtime.leases.store import RunLeaseStore


def test_cancel_run_releases_lease_and_stops_process():
    """Cancel run: tracked process is terminated, lease released."""
    fd, db = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        lease_store = RunLeaseStore(db)
        tracker = get_default_tracker()
        run_id = "cancel-test-run-1"
        lease = lease_store.acquire(run_id=run_id, worker_id="test-worker", stale_after_s=30.0)
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        stop_event = threading.Event()
        thread = threading.Thread(
            target=_heartbeat_loop,
            args=(lease_store, run_id, lease.lease_id, "test-worker", stop_event),
            kwargs={"interval_s": 2.0},
            daemon=True,
        )
        thread.start()
        tracked = TrackedRun(run_id=run_id, process=proc, lease=lease, stop_event=stop_event, thread=thread)
        tracker.register(tracked)

        result = cancel_run(run_id, lease_store)
        assert result.get("ok") is True
        assert result.get("status") == "cancelled"
        assert lease_store.get(run_id=run_id) is None
        proc.wait(timeout=5)
        assert proc.returncode is not None
    finally:
        try:
            os.unlink(db)
        except PermissionError:
            pass
