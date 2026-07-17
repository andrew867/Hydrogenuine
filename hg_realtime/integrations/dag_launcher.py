"""DagLauncher: receives RunRequested, resolves DAG from registry, invokes run_dag_job, writes run index on start. Optional lease + heartbeat. On run completion publishes RUN_COMPLETED to bus."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from ..scheduler.models import RunRequested
from .run_index_on_complete import read_run_completion_from_summary

if TYPE_CHECKING:
    from .run_index import RunIndexWriter
    from .run_tracker import RunTracker
    from ..leases.store import RunLeaseStore
    from ..bus.interface import EventBus
    from ..schemas.event import Event
    from ..schemas.event import EventType
    from ..schemas.event import stable_event_id


def _get_workspace_root() -> Optional[Path]:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _resolved_inputs_to_cli_args(resolved_inputs: Optional[Dict[str, Any]]) -> list[str]:
    """Flatten scheduler resolved_inputs into run_dag_job --input KEY=VALUE flags."""
    if not resolved_inputs:
        return []
    args: list[str] = []
    for key, value in resolved_inputs.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            text = str(value).strip()
            if text:
                args.extend(["--input", f"{key.strip()}={text}"])
    return args


def _get_job(workflow_id: str):
    """Resolve job from DAG_JOB_REGISTRY by workflow_id (job_id)."""
    root = _get_workspace_root()
    if not root:
        return None
    scripts_dir = root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from dag_runtime_jobs import get_runtime_job  # type: ignore[import-untyped]
        return get_runtime_job(workflow_id)
    except Exception:
        return None


RUN_COMPLETED_KIND = "run_completed"


def _publish_run_completed(
    run_index: Optional["RunIndexWriter"],
    bus: Optional["EventBus"],
    run_meta: Dict[str, _RunMeta],
    lock: threading.Lock,
    run_id: str,
    returncode: Optional[int],
) -> None:
    """Record completion in run index, optionally publish RUN_COMPLETED to bus, clear run meta."""
    with lock:
        meta = run_meta.pop(run_id, None)
    if not meta:
        return
    summary_status, completed_ts = read_run_completion_from_summary(meta.run_dir)
    if summary_status:
        status = summary_status
    else:
        status = "completed" if (returncode is not None and returncode == 0) else "failed"
        completed_ts = time.time()
    if run_index and hasattr(run_index, "record_completion"):
        run_index.record_completion(run_id=run_id, status=status, completed_ts=completed_ts)
    if bus is None:
        return
    from ..schemas.event import Event, EventType, stable_event_id
    payload = {
        "kind": RUN_COMPLETED_KIND,
        "correlation_id": meta.correlation_id,
        "run_id": run_id,
        "tenant_id": meta.tenant_id,
        "actor_id": meta.actor_id,
        "workflow_id": meta.workflow_id,
        "started_ts": meta.started_ts,
        "completed_ts": completed_ts,
        "status": status,
        "baseline_intent_text": "",
        "baseline_response_text": "",
        "denied_intent_texts": [],
    }
    dedup_key = f"run_completed:{meta.correlation_id}:{run_id}"
    eid = stable_event_id("internal", meta.tenant_id, dedup_key, payload)
    ev = Event(
        event_id=eid,
        event_type=EventType.INTERNAL,
        tenant_id=meta.tenant_id,
        actor_id=meta.actor_id,
        correlation_id=meta.correlation_id,
        payload=payload,
        dedup_key=dedup_key,
    )
    bus.publish(ev)


@dataclass
class _RunMeta:
    correlation_id: str
    tenant_id: str
    actor_id: str
    workflow_id: str
    started_ts: float
    run_dir: str


class DagLauncher:
    """Concrete launcher: RunRequested -> run_dag_job.py, run index on start. Optional lease + heartbeat + tracker for cancel."""

    def __init__(
        self,
        *,
        workspace: Optional[Path] = None,
        run_index_writer: Optional["RunIndexWriter"] = None,
        lease_store: Optional["RunLeaseStore"] = None,
        worker_id: str = "launcher-1",
        run_tracker: Optional["RunTracker"] = None,
        heartbeat_interval_s: float = 10.0,
        stale_after_s: float = 30.0,
        bus: Optional["EventBus"] = None,
    ) -> None:
        self._workspace = workspace or _get_workspace_root() or Path.cwd()
        self._run_index: Optional[RunIndexWriter] = run_index_writer
        self._lease_store = lease_store
        self._worker_id = worker_id
        self._run_tracker = run_tracker
        self._heartbeat_interval_s = heartbeat_interval_s
        self._stale_after_s = stale_after_s
        self._bus = bus
        self._run_meta: Dict[str, _RunMeta] = {}
        self._run_meta_lock = threading.Lock()

    def launch(self, req: RunRequested, run_id: Optional[str] = None) -> str:
        job = _get_job(req.workflow_id)
        if not job:
            raise ValueError(f"Unknown workflow_id (job_id): {req.workflow_id}")
        job_id = getattr(job, "job_id", req.workflow_id)
        if run_id is None:
            run_id = str(uuid.uuid4())
        else:
            run_id = str(run_id)
        run_dir = self._workspace / "memory" / "automation" / "dag_runs" / job_id / run_id
        started_ts = time.time()

        with self._run_meta_lock:
            self._run_meta[run_id] = _RunMeta(
                correlation_id=req.correlation_id,
                tenant_id=req.tenant_id,
                actor_id=req.actor_id,
                workflow_id=req.workflow_id,
                started_ts=started_ts,
                run_dir=str(run_dir),
            )

        lease = None
        if self._lease_store:
            lease = self._lease_store.acquire(run_id=run_id, worker_id=self._worker_id, stale_after_s=self._stale_after_s)

        if self._run_index:
            self._run_index.record_start(
                run_id=run_id,
                workflow_id=req.workflow_id,
                job_id=job_id,
                status="running",
                correlation_id=req.correlation_id,
                run_dir=str(run_dir),
            )

        run_dir.mkdir(parents=True, exist_ok=True)
        script_dir = self._workspace / "scripts"
        cmd = [
            sys.executable,
            str(script_dir / "run_dag_job.py"),
            "--job-id",
            job_id,
            "--run-id",
            run_id,
            "--workspace",
            str(self._workspace),
            *_resolved_inputs_to_cli_args(req.resolved_inputs),
        ]

        if self._lease_store and lease is not None:
            from .run_tracker import TrackedRun, _heartbeat_loop, get_default_tracker
            tracker = self._run_tracker if self._run_tracker is not None else get_default_tracker()
            proc = subprocess.Popen(
                cmd,
                cwd=str(self._workspace),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            stop_event = threading.Event()
            thread_hb = threading.Thread(
                target=_heartbeat_loop,
                args=(self._lease_store, run_id, lease.lease_id, self._worker_id, stop_event),
                kwargs={"interval_s": self._heartbeat_interval_s},
                daemon=True,
                name=f"heartbeat-{run_id[:8]}",
            )
            thread_hb.start()

            def waiter():
                proc.wait()
                stop_event.set()
                tracker.unregister(run_id)
                self._lease_store.release(run_id)
                _publish_run_completed(
                    self._run_index,
                    self._bus,
                    self._run_meta,
                    self._run_meta_lock,
                    run_id,
                    proc.returncode,
                )

            threading.Thread(target=waiter, daemon=True, name=f"waiter-{run_id[:8]}").start()
            tracked = TrackedRun(run_id=run_id, process=proc, lease=lease, stop_event=stop_event, thread=thread_hb)
            tracker.register(tracked)
        else:
            subprocess.Popen(
                cmd,
                cwd=str(self._workspace),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        return run_id
