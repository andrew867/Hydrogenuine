import time
import uuid

from hg_realtime.bus.memory_bus import InMemoryBus
from hg_realtime.schemas.event import Event, EventType, stable_event_id

from hg_cognition.schemas.trace import StepTrace, ToolCallTrace
from hg_cognition.persona.quad import QuadCoords
from hg_cognition.integrations.memory_impls import InMemoryTraceStore, InMemoryPersonaStore, JsonlArtifactStore, PrintSteeringSink

from hg_bridge.bridge_scheduler import CognitionBridgeScheduler, RUN_COMPLETED, IDLE_TICK
from hg_bridge.meditation_worker import MeditationWorker

class CaptureSteering(PrintSteeringSink):
    def __init__(self):
        self.recs = []
    def submit(self, recs):
        self.recs.extend(recs)

def test_run_completed_triggers_meditation(tmp_path):
    bus = InMemoryBus()
    corr = f"c_{uuid.uuid4().hex[:6]}"
    now = time.time()

    steps = [
        StepTrace(
            ts=now-2, correlation_id=corr, run_id="r1", node_id="n1",
            actor_id="human", role="human", input_text="safe verified", output_text="",
            constraints=["safe"], constraints_satisfied=["safe"],
            verifications_expected=1, verifications_performed=1,
            planned_alternatives=1, tool_calls=[], notes={}
        ),
        StepTrace(
            ts=now-1, correlation_id=corr, run_id="r1", node_id="n2",
            actor_id="agent", role="agent", input_text="", output_text="Definitely maybe.",
            constraints=["safe"], constraints_satisfied=[],
            verifications_expected=1, verifications_performed=0,
            planned_alternatives=0,
            tool_calls=[ToolCallTrace(tool_name="x", idempotency_key="k", args={}, ok=False, policy_denied=True, ts=now-1)],
            notes={"contradictions_found": 1}
        ),
    ]

    trace_store = InMemoryTraceStore(steps)
    persona_store = InMemoryPersonaStore()
    persona_store.save_history("human", [QuadCoords(0,0,0.2)])
    persona_store.save_history("agent", [QuadCoords(0,0,0.2)])
    artifact_path = tmp_path / "reports.jsonl"
    artifact_store = JsonlArtifactStore(str(artifact_path))
    steering = CaptureSteering()

    payload = {
        "kind": RUN_COMPLETED,
        "correlation_id": corr,
        "run_id": "r1",
        "workflow_id": "w1",
        "started_ts": now-5,
        "completed_ts": now-1,
        "status": "success",
        "baseline_intent_text": steps[0].input_text,
        "baseline_response_text": "safe verified",
        "denied_intent_texts": ["bypass policies"],
    }
    dedup_key = f"run_completed:{corr}:r1"
    eid = stable_event_id("internal", "t", dedup_key, payload)
    bus.publish(Event(event_id=eid, event_type=EventType.INTERNAL, tenant_id="t", actor_id="system", correlation_id=corr, payload=payload, dedup_key=dedup_key))

    bridge = CognitionBridgeScheduler(bus=bus)
    worker = MeditationWorker(bus=bus, trace_store=trace_store, persona_store=persona_store, artifact_store=artifact_store, steering_sink=steering)

    assert bridge.tick_once() == 1
    assert worker.tick_once() == 1

    txt = artifact_path.read_text(encoding="utf-8")
    assert "meditation" in txt or "scores" in txt
    assert len(steering.recs) >= 1


def test_idle_tick_triggers_meditation_requested():
    """IDLE_TICK when idle_min_s exceeded consumes one pending entry and emits MEDITATION_REQUESTED."""
    bus = InMemoryBus()
    corr = f"c_{uuid.uuid4().hex[:6]}"
    now = time.time()
    tenant_id, actor_id = "t1", "system"  # match RUN_COMPLETED event's tenant_id/actor_id for pending

    payload = {
        "kind": RUN_COMPLETED,
        "correlation_id": corr,
        "run_id": "r1",
        "workflow_id": "w1",
        "started_ts": now - 5,
        "completed_ts": now - 1,
        "status": "success",
        "baseline_intent_text": "intent",
        "baseline_response_text": "response",
        "denied_intent_texts": [],
    }
    dedup_key = f"run_completed:{corr}:r1"
    eid = stable_event_id("internal", tenant_id, dedup_key, payload)
    bus.publish(Event(
        event_id=eid, event_type=EventType.INTERNAL,
        tenant_id=tenant_id, actor_id=actor_id, correlation_id=corr,
        payload=payload, dedup_key=dedup_key,
    ))

    bridge = CognitionBridgeScheduler(bus=bus)
    assert bridge.tick_once() == 1  # RUN_COMPLETED -> MEDITATION_REQUESTED + pending entry

    # IDLE_TICK with now_ts so that (now_ts - last_idle) >= idle_min_s (default 30); last_idle is 0
    idle_payload = {
        "kind": IDLE_TICK,
        "now_ts": 100.0,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
    }
    idle_eid = stable_event_id("internal", tenant_id, "idle_tick_1", idle_payload)
    bus.publish(Event(
        event_id=idle_eid, event_type=EventType.INTERNAL,
        tenant_id=tenant_id, actor_id=actor_id, correlation_id=corr,
        payload=idle_payload, dedup_key="idle_tick_1",
    ))

    # First poll may return the MEDITATION_REQUESTED from RUN_COMPLETED; second event is IDLE_TICK
    handled = bridge.tick_once()
    assert handled == 1, "IDLE_TICK should consume one pending and emit MEDITATION_REQUESTED"


def test_worker_skips_empty_meditation_windows(tmp_path):
    bus = InMemoryBus()
    corr = f"c_{uuid.uuid4().hex[:6]}"
    now = time.time()

    trace_store = InMemoryTraceStore([])
    persona_store = InMemoryPersonaStore()
    artifact_path = tmp_path / "reports.jsonl"
    artifact_store = JsonlArtifactStore(str(artifact_path))
    steering = CaptureSteering()

    payload = {
        "kind": "meditation_requested",
        "correlation_id": corr,
        "window_start_ts": now - 5,
        "window_end_ts": now,
        "baseline_intent_text": "",
        "baseline_response_text": "",
        "denied_intent_texts": [],
    }
    dedup_key = f"meditate:{corr}"
    eid = stable_event_id("internal", "t", dedup_key, payload)
    bus.publish(Event(event_id=eid, event_type=EventType.INTERNAL, tenant_id="t", actor_id="system", correlation_id=corr, payload=payload, dedup_key=dedup_key))

    worker = MeditationWorker(bus=bus, trace_store=trace_store, persona_store=persona_store, artifact_store=artifact_store, steering_sink=steering)
    assert worker.tick_once() == 1
    assert not artifact_path.exists()
    assert steering.recs == []
