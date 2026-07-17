"""Timer source: at configured times emits TIMER events into EventBus. Deterministic event_id/dedup_key for (job_id, tick)."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..bus.interface import EventBus
from ..schemas.event import Event, EventType, stable_event_id
from .schedule_config import ScheduleEntry, ScheduleState, clear_cadence_override_for_entry, load_schedule

logger = logging.getLogger(__name__)

DEFAULT_TENANT_ID = "default"
DEFAULT_ACTOR_ID = "timer-source"
DEFAULT_CORRELATION_PREFIX = "timer"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _tick_key(job_id: str, due: datetime) -> str:
    """Deterministic dedup_key for (job_id, tick). Coalescer can dedupe on this."""
    ts = int(due.timestamp())
    return f"timer:{job_id}:{ts}"


def _publish_timer(
    bus: EventBus,
    entry: ScheduleEntry,
    due: datetime,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    actor_id: str = DEFAULT_ACTOR_ID,
) -> None:
    payload_inputs = dict(entry.inputs) if entry.inputs else {"trigger": "realtime", "goal": f"scheduled {entry.job_id}"}
    workflow_id = str(payload_inputs.pop("workflow_id", "") or "").strip()
    payload = {
        "job_id": entry.job_id,
        "inputs": payload_inputs,
    }
    if workflow_id:
        payload["workflow_id"] = workflow_id
    dedup_key = _tick_key(entry.job_id, due)
    correlation_id = f"{DEFAULT_CORRELATION_PREFIX}:{entry.job_id}:{int(due.timestamp())}"
    event_id = stable_event_id(EventType.TIMER.value, tenant_id, dedup_key, payload)
    event = Event(
        event_id=event_id,
        event_type=EventType.TIMER,
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload=payload,
        dedup_key=dedup_key,
    )
    bus.publish(event)
    logger.debug("timer published job_id=%s dedup_key=%s", entry.job_id, dedup_key)


def fire_due_events(
    bus: EventBus,
    state: ScheduleState,
    now: Optional[datetime] = None,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    actor_id: str = DEFAULT_ACTOR_ID,
) -> int:
    """Publish TIMER for all entries due at or before now. Returns number published."""
    ref = now or _utc_now()
    count = 0
    while True:
        due_result = state.next_due(ref)
        if due_result is None:
            break
        due_time, entry = due_result
        if due_time > ref:
            break
        _publish_timer(bus, entry, due_time, tenant_id=tenant_id, actor_id=actor_id)
        clear_cadence_override_for_entry(entry, state.workspace_root)
        state.mark_fired(entry, ref)
        count += 1
    return count


def run_timer_loop(
    bus: EventBus,
    state: ScheduleState,
    *,
    tenant_id: str = DEFAULT_TENANT_ID,
    actor_id: str = DEFAULT_ACTOR_ID,
    stop_event: Optional[threading.Event] = None,
    sleep_cap_s: float = 60.0,
) -> None:
    """
    Loop: sleep until next due time, publish TIMER for all due entries, repeat.
    Stops when stop_event is set.
    """
    stop = stop_event or threading.Event()
    while not stop.is_set():
        now = _utc_now()
        n = fire_due_events(bus, state, now, tenant_id=tenant_id, actor_id=actor_id)
        if n > 0:
            time.sleep(0.1)
            continue
        due_result = state.next_due(now)
        if due_result is None:
            time.sleep(min(1.0, sleep_cap_s))
            continue
        due_time, _ = due_result
        sleep_s = min((due_time - now).total_seconds(), sleep_cap_s)
        if sleep_s > 0:
            stop.wait(timeout=sleep_s)


def start_timer_thread(
    bus: EventBus,
    schedule_path_or_state: Optional[Path] | ScheduleState = None,
    *,
    workspace_root: Optional[Path] = None,
    tenant_id: str = DEFAULT_TENANT_ID,
    actor_id: str = DEFAULT_ACTOR_ID,
    daemon: bool = True,
) -> tuple[threading.Thread, threading.Event]:
    """
    Load schedule (if not already ScheduleState), start timer loop in a thread.
    Returns (thread, stop_event). Call stop_event.set() then thread.join() to stop.
    """
    if isinstance(schedule_path_or_state, ScheduleState):
        state = schedule_path_or_state
    else:
        state = load_schedule(workspace_root)
    stop = threading.Event()
    thread = threading.Thread(
        target=run_timer_loop,
        kwargs={
            "bus": bus,
            "state": state,
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "stop_event": stop,
        },
        daemon=daemon,
        name="hg-realtime-timer",
    )
    thread.start()
    return thread, stop
