import uuid

import pytest

from hg_realtime.integrations.workflow_mapping import route_event_to_workflow
from hg_realtime.schemas.event import Event, EventType


@pytest.fixture(autouse=True)
def _disable_release_gate(monkeypatch):
    monkeypatch.setenv("HG_RELEASE_GATE_ENFORCED", "0")


def test_route_event_to_workflow_routes_scheduled_social_jobs_to_unified_social_media():
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="timer-source",
        correlation_id="c1",
        payload={"job_id": "fourclaw-auto-post-cadence", "inputs": {"goal": "scheduled check"}},
        dedup_key="k1",
    )

    workflow_id, resolved_inputs = route_event_to_workflow(event)

    assert workflow_id == "social-media"
    assert resolved_inputs["task_name"] == "fourclaw-auto-post"
    assert resolved_inputs["preferred_task_name"] == "fourclaw-auto-post"
    assert resolved_inputs["platform"] == "fourclaw"
    assert resolved_inputs["mode"] == "auto-post"
    assert resolved_inputs["platforms"] == ["fourclaw"]
    assert resolved_inputs["requested_job_id"] == "fourclaw-auto-post-cadence"
    assert resolved_inputs["scheduler_model"] == "single_entity_directed_cadence"
    assert resolved_inputs["goal"] == "scheduled check"


def test_route_event_to_workflow_routes_direct_social_jobs_to_unified_social_media():
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="timer-source",
        correlation_id="c1",
        payload={"job_id": "moltbook-engage", "inputs": {"trigger": "realtime"}},
        dedup_key="k2",
    )

    workflow_id, resolved_inputs = route_event_to_workflow(event)

    assert workflow_id == "social-media"
    assert resolved_inputs["task_name"] == "moltbook-engage"
    assert resolved_inputs["platform"] == "moltbook"
    assert resolved_inputs["mode"] == "engage"
    assert resolved_inputs["platforms"] == ["moltbook"]
    assert resolved_inputs["requested_job_id"] == "moltbook-engage"


def test_route_event_to_workflow_leaves_non_social_jobs_unchanged():
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="timer-source",
        correlation_id="c1",
        payload={"job_id": "overseer-monitor", "inputs": {"trigger": "realtime"}},
        dedup_key="k3",
    )

    workflow_id, resolved_inputs = route_event_to_workflow(event)

    assert workflow_id == "overseer-monitor"
    assert resolved_inputs["trigger"] == "realtime"


def test_route_event_to_workflow_preserves_scheduler_alias_for_explicit_workflow():
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TIMER,
        tenant_id="t1",
        actor_id="timer-source",
        correlation_id="c1",
        payload={
            "job_id": "social-media-underling",
            "workflow_id": "social-media",
            "inputs": {"task_name": "fourclaw-engage", "trigger": "realtime"},
        },
        dedup_key="k4",
    )

    workflow_id, resolved_inputs = route_event_to_workflow(event)

    assert workflow_id == "social-media"
    assert resolved_inputs["task_name"] == "fourclaw-engage"
    assert resolved_inputs["scheduler_job_id"] == "social-media-underling"
    assert resolved_inputs["requested_job_id"] == "social-media-underling"
