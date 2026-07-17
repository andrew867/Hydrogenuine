"""RedisStreamsBus tests using fakeredis (no real Redis required)."""

import uuid
import pytest

try:
    import fakeredis
except ImportError:
    fakeredis = None  # type: ignore[assignment]


@pytest.mark.skipif(fakeredis is None, reason="fakeredis not installed")
def test_redis_bus_publish_poll_ack():
    from hg_realtime.bus.redis_streams_bus import RedisStreamsBus
    from hg_realtime.schemas.event import Event, EventType

    client = fakeredis.FakeRedis(decode_responses=True)
    bus = RedisStreamsBus(redis_url="redis://localhost/0", client=client)

    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t",
        actor_id="system",
        correlation_id="c1",
        payload={"workflow_id": "w1", "inputs": {}},
    )
    bus.publish(e)
    got = bus.poll(group="g", consumer="c1", max_events=10, timeout_s=0.5)
    assert len(got) == 1
    assert got[0].event_id == e.event_id
    assert got[0].payload.get("workflow_id") == "w1"
    bus.ack(group="g", consumer="c1", event_id=e.event_id)
    # Second poll should not see it again (acked)
    got2 = bus.poll(group="g", consumer="c1", max_events=10, timeout_s=0.1)
    assert len(got2) == 0


@pytest.mark.skipif(fakeredis is None, reason="fakeredis not installed")
def test_redis_bus_second_consumer_does_not_see_acked():
    from hg_realtime.bus.redis_streams_bus import RedisStreamsBus
    from hg_realtime.schemas.event import Event, EventType

    client = fakeredis.FakeRedis(decode_responses=True)
    bus = RedisStreamsBus(redis_url="redis://localhost/0", client=client)

    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t",
        actor_id="system",
        correlation_id="c1",
        payload={"job_id": "fourclaw-auto-post-cadence"},
    )
    bus.publish(e)
    # Consumer 1 polls and acks
    got1 = bus.poll(group="hg-scheduler", consumer="sched-1", max_events=10, timeout_s=0.5)
    assert len(got1) == 1
    bus.ack(group="hg-scheduler", consumer="sched-1", event_id=got1[0].event_id)
    # Consumer 2 in same group gets nothing (message was acked)
    got2 = bus.poll(group="hg-scheduler", consumer="sched-2", max_events=10, timeout_s=0.1)
    assert len(got2) == 0


@pytest.mark.skipif(fakeredis is None, reason="fakeredis not installed")
def test_scheduler_tick_with_redis_bus_emits_run_requested():
    from hg_realtime.bus.redis_streams_bus import RedisStreamsBus
    from hg_realtime.schemas.event import Event, EventType
    from hg_realtime.scheduler.service import RealTimeScheduler
    from hg_realtime.scheduler.models import RunRequested
    from hg_realtime.integrations.dag_launcher import DagLauncher
    from hg_realtime.integrations.policy_gate import PolicyGate

    client = fakeredis.FakeRedis(decode_responses=True)
    bus = RedisStreamsBus(redis_url="redis://localhost/0", client=client)

    class CaptureLauncher(DagLauncher):
        def __init__(self):
            self.launched = []

        def launch(self, req: RunRequested) -> str:
            self.launched.append(req)
            return "run_captured"

    launcher = CaptureLauncher()
    policy = PolicyGate()
    sched = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy)

    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="system",
        correlation_id="c1",
        payload={"workflow_id": "w1", "inputs": {"k": "v"}},
        dedup_key="dk1",
    )
    bus.publish(e)
    handled = sched.tick_once()
    assert handled == 1
    assert len(launcher.launched) == 1
    assert launcher.launched[0].workflow_id == "w1"
    assert launcher.launched[0].resolved_inputs.get("k") == "v"
