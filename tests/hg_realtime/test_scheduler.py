import uuid
from dataclasses import dataclass

import pytest

from hg_realtime.bus.memory_bus import InMemoryBus
from hg_realtime.schemas.event import Event, EventType
from hg_realtime.scheduler.service import RealTimeScheduler
from hg_realtime.scheduler.models import RunRequested
from hg_realtime.integrations.dag_launcher import DagLauncher
from hg_realtime.integrations.policy_gate import PolicyGate, PolicyDecision


@pytest.fixture(autouse=True)
def _disable_release_gate(monkeypatch):
    monkeypatch.setenv("HG_RELEASE_GATE_ENFORCED", "0")

@dataclass
class CaptureLauncher(DagLauncher):
    launched: list[RunRequested]
    def launch(self, req: RunRequested) -> str:
        self.launched.append(req)
        return "run_x"

class DenyPolicy(PolicyGate):
    def allow_run(self, **kwargs):
        return PolicyDecision(False, "nope")

def test_scheduler_launches_on_timer_event():
    bus = InMemoryBus()
    launcher = CaptureLauncher(launched=[])
    policy = PolicyGate()
    sched = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy)

    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="system",
        correlation_id="c1",
        payload={"workflow_id": "w1", "inputs": {"k": "v"}},
        dedup_key="k1",
    )
    bus.publish(e)
    handled = sched.tick_once()
    assert handled == 1
    assert len(launcher.launched) == 1
    assert launcher.launched[0].workflow_id == "w1"

def test_scheduler_respects_policy_gate():
    bus = InMemoryBus()
    launcher = CaptureLauncher(launched=[])
    policy = DenyPolicy()
    sched = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy)

    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="system",
        correlation_id="c1",
        payload={"workflow_id": "w1", "inputs": {"k": "v"}},
        dedup_key="k1",
    )
    bus.publish(e)
    handled = sched.tick_once()
    assert handled == 0
    assert len(launcher.launched) == 0


def test_scheduler_swarm_timer_invokes_swarm_controller():
    """TIMER with payload.swarm_tasks routes to swarm; SwarmController.run(plan) is invoked."""
    from unittest.mock import MagicMock, patch
    from hg_realtime.swarm.contracts import SwarmResult

    bus = InMemoryBus()
    launcher = CaptureLauncher(launched=[])
    policy = PolicyGate()
    sched = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy)

    run_calls = []

    def capture_run(plan):
        run_calls.append(plan)
        return SwarmResult(
            swarm_run_id="swarm-1",
            correlation_id=plan.correlation_id,
            child_run_ids=[],
            child_outputs=[],
            child_statuses=[],
            status="completed",
            counts={"launched": 0, "completed": 0, "failed": 0},
            summary="",
            artifacts={},
            warnings=[],
            artifacts_path=None,
        )

    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="system",
        correlation_id="swarm-c",
        payload={
            "swarm_tasks": [
                {"workflow_id": "job-a", "inputs": {"x": 1}},
                {"workflow_id": "job-b", "inputs": {"x": 2}},
            ],
            "max_children": 10,
        },
        dedup_key="sk1",
    )
    bus.publish(e)

    with patch("hg_realtime.swarm.SwarmController") as MockController:
        MockController.return_value.run.side_effect = capture_run
        handled = sched.tick_once()

    assert handled == 1
    assert len(run_calls) == 1
    plan = run_calls[0]
    assert len(plan.tasks) == 2
    assert plan.tasks[0]["workflow_id"] == "job-a"
    assert plan.tasks[1]["workflow_id"] == "job-b"
    assert plan.max_children == 10
