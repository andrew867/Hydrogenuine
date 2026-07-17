"""Track launched runs (process + lease + heartbeat thread) for cancel and lifecycle."""

from __future__ import annotations

import logging
import subprocess
import threading
from dataclasses import dataclass
from typing import Dict, Optional

from ..leases.store import Lease, RunLeaseStore

logger = logging.getLogger(__name__)

DEFAULT_HEARTBEAT_INTERVAL_S = 10.0


@dataclass
class TrackedRun:
    run_id: str
    process: subprocess.Popen
    lease: Lease
    stop_event: threading.Event
    thread: threading.Thread

    def stop_heartbeat(self, timeout_s: float = 5.0) -> None:
        self.stop_event.set()
        self.thread.join(timeout=timeout_s)


def _heartbeat_loop(
    lease_store: RunLeaseStore,
    run_id: str,
    lease_id: str,
    worker_id: str,
    stop_event: threading.Event,
    interval_s: float = DEFAULT_HEARTBEAT_INTERVAL_S,
) -> None:
    seq = 1
    while not stop_event.is_set():
        stop_event.wait(timeout=interval_s)
        if stop_event.is_set():
            break
        try:
            lease_store.heartbeat(run_id=run_id, lease_id=lease_id, worker_id=worker_id, seq=seq)
            seq += 1
        except Exception as e:
            logger.warning("heartbeat failed run_id=%s: %s", run_id, e)
            break


class RunTracker:
    """Registry of run_id -> TrackedRun. Used by launcher to register and by cancel to find process + lease."""

    def __init__(self) -> None:
        self._by_run_id: Dict[str, TrackedRun] = {}
        self._lock = threading.RLock()

    def register(self, tracked: TrackedRun) -> None:
        with self._lock:
            self._by_run_id[tracked.run_id] = tracked

    def unregister(self, run_id: str) -> Optional[TrackedRun]:
        with self._lock:
            return self._by_run_id.pop(run_id, None)

    def get(self, run_id: str) -> Optional[TrackedRun]:
        with self._lock:
            return self._by_run_id.get(run_id)

    def cancel(
        self,
        run_id: str,
        lease_store: RunLeaseStore,
        *,
        terminate_timeout_s: float = 5.0,
        kill_fallback: bool = True,
    ) -> bool:
        """
        Stop heartbeat, terminate process, release lease. Returns True if run was tracked and cancelled.
        """
        tracked = self.unregister(run_id)
        if tracked is None:
            lease_store.release(run_id)
            return False
        tracked.stop_heartbeat(timeout_s=terminate_timeout_s)
        try:
            if tracked.process.poll() is None:
                tracked.process.terminate()
                try:
                    tracked.process.wait(timeout=terminate_timeout_s)
                except subprocess.TimeoutExpired:
                    if kill_fallback:
                        tracked.process.kill()
                    tracked.process.wait()
        except Exception as e:
            logger.warning("cancel run_id=%s terminate/kill: %s", run_id, e)
        lease_store.release(run_id)
        return True


# Module-level default tracker for launcher and cancel_run to share
_default_tracker: Optional[RunTracker] = None
_tracker_lock = threading.Lock()


def get_default_tracker() -> RunTracker:
    global _default_tracker
    with _tracker_lock:
        if _default_tracker is None:
            _default_tracker = RunTracker()
        return _default_tracker


