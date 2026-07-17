"""Timer source: fire_due_events and integration with scheduler."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from hg_realtime.schemas.event import EventType
from hg_realtime.scheduler.schedule_config import ScheduleEntry, ScheduleState
from hg_realtime.scheduler.timer_source import fire_due_events


@pytest.fixture(autouse=True)
def _disable_release_gate(monkeypatch):
    monkeypatch.setenv("HG_RELEASE_GATE_ENFORCED", "0")


class RecordingBus:
    """Records published events; no poll/ack."""

    def __init__(self):
        self.published: list = []

    def publish(self, event) -> None:
        self.published.append(event)

    def poll(self, **kwargs):
        return []

    def ack(self, **kwargs):
        pass


def test_timer_fires_one_due_entry():
    """One entry due at now -> exactly one publish with TIMER and payload.job_id."""
    bus = RecordingBus()
    now = datetime.now(timezone.utc)
    entry1 = ScheduleEntry(job_id="job-a", interval_minutes=15)
    entry2 = ScheduleEntry(job_id="job-b", interval_minutes=30)
    state = ScheduleState(entries=[entry1, entry2])
    state.next_run["job-a"] = now - timedelta(seconds=1)
    state.next_run["job-b"] = now + timedelta(minutes=10)
    n = fire_due_events(bus, state, now)
    assert n == 1
    assert len(bus.published) == 1
    assert bus.published[0].event_type == EventType.TIMER
    assert bus.published[0].payload.get("job_id") == "job-a"
    assert bus.published[0].dedup_key is not None
    assert "timer:job-a:" in (bus.published[0].dedup_key or "")


def test_timer_integration_scheduler_launcher():
    """Timer + in-memory bus + scheduler + capture launcher route a persona-scoped social alias through social-media."""
    from hg_realtime.bus.memory_bus import InMemoryBus
    from hg_realtime.scheduler.models import RunRequested
    from hg_realtime.scheduler.service import RealTimeScheduler
    from hg_realtime.integrations.dag_launcher import DagLauncher
    from hg_realtime.integrations.policy_gate import PolicyGate

    bus = InMemoryBus()
    launched: list[RunRequested] = []

    class CaptureLauncher(DagLauncher):
        def launch(self, req: RunRequested) -> str:
            launched.append(req)
            return "run-1"

    launcher = CaptureLauncher()
    policy = PolicyGate()
    scheduler = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy)

    now = datetime.now(timezone.utc)
    entry = ScheduleEntry(
        job_id="social-media-underling",
        interval_minutes=60,
        inputs={"workflow_id": "social-media", "task_name": "fourclaw-engage", "trigger": "realtime"},
    )
    state = ScheduleState(entries=[entry])
    state.next_run[entry.job_id] = now - timedelta(seconds=1)
    fire_due_events(bus, state, now)
    handled = scheduler.tick_once()
    assert handled == 1
    assert len(launched) == 1
    assert launched[0].workflow_id == "social-media"
    assert launched[0].resolved_inputs.get("task_name") == "fourclaw-engage"
    assert launched[0].resolved_inputs.get("trigger") == "realtime"
    assert launched[0].resolved_inputs.get("scheduler_job_id") == "social-media-underling"


def test_timer_honors_persona_cadence_override_and_clears_it(tmp_path):
    """A persona-scoped social alias should honor cadence_request.json and consume it when fired."""
    now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
    override_dir = tmp_path / "memory" / "automation" / "automation-underling-chan"
    override_dir.mkdir(parents=True, exist_ok=True)
    override_path = override_dir / "cadence_request.json"
    override_path.write_text(
        json.dumps(
            {
                "task": "fourclaw-engage",
                "job_id": "social-media-underling",
                "requested_at": "2026-03-13T12:00:00Z",
                "not_before": "2026-03-13T12:03:00Z",
                "requested_duration_minutes": 3,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    bus = RecordingBus()
    entry = ScheduleEntry(
        job_id="social-media-underling",
        interval_minutes=11,
        inputs={"workflow_id": "social-media", "task_name": "fourclaw-engage", "trigger": "realtime"},
    )
    state = ScheduleState(entries=[entry], workspace_root=tmp_path)

    assert fire_due_events(bus, state, now + timedelta(minutes=2)) == 0
    assert fire_due_events(bus, state, now + timedelta(minutes=3)) == 1
    assert len(bus.published) == 1
    assert bus.published[0].payload.get("job_id") == "social-media-underling"
    assert not override_path.exists()


def test_e2e_timer_run_index_and_launcher():
    """E2E: fire one TIMER, scheduler runs, launcher invoked and run index updated."""
    import os
    import tempfile
    from hg_realtime.bus.memory_bus import InMemoryBus
    from hg_realtime.scheduler.models import RunRequested
    from hg_realtime.scheduler.service import RealTimeScheduler
    from hg_realtime.integrations.dag_launcher import DagLauncher
    from hg_realtime.integrations.policy_gate import PolicyGate
    from hg_realtime.integrations.run_index import SqliteRunIndexWriter

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        run_index = SqliteRunIndexWriter(sqlite_path=db_path)
        launched: list[RunRequested] = []

        class CaptureAndIndexLauncher(DagLauncher):
            def launch(self, req: RunRequested) -> str:
                launched.append(req)
                run_id = f"e2e-{len(launched)}"
                run_index.record_start(
                    run_id=run_id,
                    workflow_id=req.workflow_id,
                    status="running",
                    correlation_id=req.correlation_id,
                )
                return run_id

        bus = InMemoryBus()
        launcher = CaptureAndIndexLauncher()
        scheduler = RealTimeScheduler(bus=bus, launcher=launcher, policy=PolicyGate())
        now = datetime.now(timezone.utc)
        entry = ScheduleEntry(job_id="overseer-monitor", interval_minutes=15)
        state = ScheduleState(entries=[entry])
        state.next_run[entry.job_id] = now - timedelta(seconds=1)
        fire_due_events(bus, state, now)
        handled = scheduler.tick_once()
        assert handled == 1
        assert len(launched) == 1
        import sqlite3
        with sqlite3.connect(db_path) as c:
            row = c.execute("SELECT run_id, graph_id, status FROM runs").fetchone()
        assert row is not None
        assert row[1] == "overseer-monitor"
        assert row[2] == "running"
    finally:
        try:
            os.unlink(db_path)
        except PermissionError:
            pass
