from hg_realtime.schemas.event import Event, EventType, stable_event_id

def test_event_roundtrip():
    payload = {"a": 1}
    eid = stable_event_id("timer", "t1", "k1", payload)
    e = Event(
        event_id=eid,
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="system",
        correlation_id="c1",
        payload=payload,
        dedup_key="k1",
    )
    e.validate()
    d = e.to_dict()
    e2 = Event.from_dict(d)
    assert e2.event_id == e.event_id
    assert e2.event_type == e.event_type
    assert e2.payload == e.payload
