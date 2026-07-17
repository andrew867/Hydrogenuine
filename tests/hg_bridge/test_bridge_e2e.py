"""E2E test: run index + events.jsonl -> RUN_COMPLETED -> bridge -> meditation worker -> report + steering (real TraceStore)."""

import json
import time
import uuid
from pathlib import Path

import pytest

from hg_realtime.bus.memory_bus import InMemoryBus
from hg_realtime.schemas.event import Event, EventType, stable_event_id
from hg_realtime.integrations.run_index import SqliteRunIndexWriter
from hg_cognition.integrations.memory_impls import JsonlArtifactStore

from hg_bridge.bridge_scheduler import CognitionBridgeScheduler, RUN_COMPLETED
from hg_bridge.meditation_worker import MeditationWorker
from hg_bridge.integrations import RunDirTraceStore, FilePersonaStore, ContextualSteeringSink
from hg_realtime.steering.file_adapter import FileSteeringAdapter


class CaptureSteeringAdapter:
    """Captures submitted steering events for assertion."""

    def __init__(self):
        self.events = []

    def submit(self, evt):
        self.events.append(evt)


def test_bridge_e2e_real_trace_store_run_index(tmp_path):
    """E2E: run index with run_dir + events.jsonl, RUN_COMPLETED on bus -> bridge -> worker -> report file + steering."""
    bus = InMemoryBus()
    corr = f"e2e_{uuid.uuid4().hex[:8]}"
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    run_dir = tmp_path / "dag_runs" / "job1" / run_id
    run_dir.mkdir(parents=True)

    # Write minimal events.jsonl (at least one dag_node_completed)
    events_path = run_dir / "events.jsonl"
    now_ts = time.time()
    events_path.write_text(
        json.dumps({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts - 2)),
            "event": "dag_run_started",
            "graph_id": "job1",
            "run_id": run_id,
        }) + "\n"
        + json.dumps({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts - 1)),
            "event": "dag_node_completed",
            "graph_id": "job1",
            "run_id": run_id,
            "node_id": "n1",
            "status": "done",
        }) + "\n",
        encoding="utf-8",
    )

    # Run index: record_start then record_completion with run_dir and correlation_id
    db_path = str(tmp_path / "runs.db")
    run_index = SqliteRunIndexWriter(sqlite_path=db_path)
    run_index.record_start(
        run_id=run_id,
        workflow_id="job1",
        job_id="job1",
        status="running",
        correlation_id=corr,
        run_dir=str(run_dir),
    )
    run_index.record_completion(run_id=run_id, status="completed", completed_ts=now_ts)

    # Stores
    trace_store = RunDirTraceStore(run_index)
    persona_store = FilePersonaStore(tmp_path / "persona")
    artifact_path = tmp_path / "reports.jsonl"
    artifact_store = JsonlArtifactStore(str(artifact_path))
    steering_capture = CaptureSteeringAdapter()
    steering_sink = ContextualSteeringSink(steering_capture)

    # Publish RUN_COMPLETED
    payload = {
        "kind": RUN_COMPLETED,
        "correlation_id": corr,
        "run_id": run_id,
        "workflow_id": "job1",
        "started_ts": now_ts - 10,
        "completed_ts": now_ts,
        "status": "success",
        "baseline_intent_text": "do something",
        "baseline_response_text": "ok",
        "denied_intent_texts": [],
    }
    dedup_key = f"run_completed:{corr}:{run_id}"
    eid = stable_event_id("internal", "tenant1", dedup_key, payload)
    bus.publish(Event(
        event_id=eid,
        event_type=EventType.INTERNAL,
        tenant_id="tenant1",
        actor_id="system",
        correlation_id=corr,
        payload=payload,
        dedup_key=dedup_key,
    ))

    bridge = CognitionBridgeScheduler(bus=bus)
    worker = MeditationWorker(
        bus=bus,
        trace_store=trace_store,
        persona_store=persona_store,
        artifact_store=artifact_store,
        steering_sink=steering_sink,
    )

    bridge.tick_once()
    worker.tick_once()

    assert artifact_path.exists()
    lines = artifact_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1, "artifact file must have at least one report line"
    assert "meditation" in lines[0].lower() or "report_id" in lines[0].lower() or "scores" in lines[0].lower()

    assert len(steering_capture.events) >= 1, "steering must receive at least one recommendation"
    # No exception: we reached here after bridge_scheduler.tick_once() and meditation_worker.tick_once()
