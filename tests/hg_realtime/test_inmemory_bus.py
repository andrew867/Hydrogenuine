import uuid
from hg_realtime.bus.memory_bus import InMemoryBus
from hg_realtime.schemas.event import Event, EventType

def test_bus_publish_poll_ack():
    bus = InMemoryBus()
    e = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.INTERNAL,
        tenant_id="t",
        actor_id="a",
        correlation_id="c",
        payload={"x": 1},
    )
    bus.publish(e)
    got = bus.poll(group="g", consumer="c1", max_events=10, timeout_s=0.1)
    assert len(got) == 1
    assert got[0].event_id == e.event_id
    bus.ack(group="g", consumer="c1", event_id=e.event_id)
