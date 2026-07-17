from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from .bus.memory_bus import InMemoryBus
from .schemas.event import Event, EventType, stable_event_id
from .scheduler.service import RealTimeScheduler
from .scheduler.models import RunRequested
from .integrations.dag_launcher import DagLauncher
from .integrations.policy_gate import PolicyGate

@dataclass
class PrintLauncher(DagLauncher):
    def launch(self, req: RunRequested) -> str:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        print(f"[launcher] workflow={req.workflow_id} run_id={run_id} correlation_id={req.correlation_id} inputs={req.resolved_inputs}")
        return run_id

def main() -> None:
    bus = InMemoryBus()
    launcher = PrintLauncher()
    policy = PolicyGate()
    sched = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy)

    corr = f"corr_{uuid.uuid4().hex[:8]}"
    payload: Dict[str, Any] = {"workflow_id": "demo.workflow", "inputs": {"hello": "world"}}
    eid = stable_event_id("timer", "tenant_demo", "timer:demo.workflow", payload)

    e = Event(
        event_id=eid,
        event_type=EventType.TIMER,
        tenant_id="tenant_demo",
        actor_id="system",
        correlation_id=corr,
        payload=payload,
        dedup_key="timer:demo.workflow",
    )
    bus.publish(e)
    handled = sched.tick_once()
    print(f"[scheduler] handled={handled}")

if __name__ == "__main__":
    main()
