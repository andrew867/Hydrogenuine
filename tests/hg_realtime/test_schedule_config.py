"""Schedule config load and next_run_times."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hg_gateway.db import get_connection
from hg_realtime.scheduler.schedule_config import (
    ScheduleEntry,
    ScheduleState,
    load_schedule,
)

try:
    from croniter import croniter as _croniter
except ImportError:
    _croniter = None


def test_schedule_entry_interval():
    entry = ScheduleEntry(job_id="j1", interval_minutes=15)
    state = ScheduleState(entries=[entry])
    result = state.next_due()
    assert result is not None
    due_time, e = result
    assert e.job_id == "j1"
    assert due_time is not None


@pytest.mark.skipif(_croniter is None, reason="croniter not installed")
def test_schedule_entry_cron():
    entry = ScheduleEntry(job_id="j2", cron="0 * * * *")
    state = ScheduleState(entries=[entry])
    result = state.next_due()
    assert result is not None
    due_time, e = result
    assert e.job_id == "j2"


@pytest.mark.skipif(_croniter is None, reason="croniter not installed")
def test_load_schedule_from_fixture(tmp_path):
    config_path = tmp_path / "memory" / "automation"
    config_path.mkdir(parents=True)
    schedule = [
        {"job_id": "a", "cron": "5 * * * *"},
        {"job_id": "b", "interval_minutes": 30},
    ]
    (config_path / "realtime_schedule.json").write_text(json.dumps(schedule), encoding="utf-8")
    state = load_schedule(workspace_root=tmp_path)
    assert len(state.entries) == 2
    job_ids = {e.job_id for e in state.entries}
    assert job_ids == {"a", "b"}
    result = state.next_due()
    assert result is not None
    state.mark_fired(state.entries[0], result[0])
    next_result = state.next_due()
    assert next_result is not None


def test_load_schedule_prefers_gateway_db_and_seeds_from_legacy_file(tmp_path):
    config_path = tmp_path / "memory" / "automation"
    config_path.mkdir(parents=True)
    schedule = [
        {"job_id": "a", "cron": "5 * * * *", "inputs": {"workflow_id": "alpha"}},
        {"job_id": "b", "interval_minutes": 30, "inputs": {"workflow_id": "beta"}},
    ]
    (config_path / "realtime_schedule.json").write_text(json.dumps(schedule), encoding="utf-8")

    state = load_schedule(workspace_root=tmp_path)
    assert len(state.entries) == 2
    assert {e.job_id for e in state.entries} == {"a", "b"}

    db_path = tmp_path / "memory" / "gateway.sqlite3"
    with get_connection(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT job_id, cron, interval_minutes, inputs_json, status FROM scheduled_jobs ORDER BY job_id"
        ).fetchall()
    assert [row["job_id"] for row in rows] == ["a", "b"]
    assert rows[0]["status"] == "active"
    assert json.loads(rows[0]["inputs_json"])["workflow_id"] == "alpha"


def test_load_schedule_uses_gateway_db_over_legacy_file(tmp_path):
    config_path = tmp_path / "memory" / "automation"
    config_path.mkdir(parents=True)
    (config_path / "realtime_schedule.json").write_text(
        json.dumps(
            [
                {"job_id": "legacy-only", "interval_minutes": 5, "inputs": {"workflow_id": "legacy"}},
            ]
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "memory" / "gateway.sqlite3"
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO scheduled_jobs (tenant_id, job_id, cron, interval_minutes, inputs_json, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            ("default", "db-first", None, 10, json.dumps({"workflow_id": "db-first"}), "active"),
        )

    state = load_schedule(workspace_root=tmp_path)
    assert [entry.job_id for entry in state.entries] == ["db-first"]
    assert state.entries[0].inputs["workflow_id"] == "db-first"


def test_schedule_entry_held_lane_is_suppressed(tmp_path):
    operational_dir = tmp_path / "memory" / "automation" / "automation-underling-chan"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        json.dumps({"mode": "held", "reason": "maintenance"}), encoding="utf-8"
    )
    entry = ScheduleEntry(
        job_id="social-media-underling",
        interval_minutes=15,
        inputs={"task_name": "fourclaw-engage", "workflow_id": "social-media"},
    )
    state = ScheduleState(entries=[entry], workspace_root=tmp_path)
    result = state.next_due()
    assert result is not None
    due_time, _ = result
    assert (due_time - datetime.now(timezone.utc)).days >= 3000


def test_schedule_entry_budget_exhausted_waits_for_budget_reset(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    operational_dir = tmp_path / "memory" / "automation" / "automation-underling-chan"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        json.dumps({"mode": "normal", "daily_outbound_budget": 1, "outbound_actions_window_hours": 24}),
        encoding="utf-8",
    )
    from hg_gateway import keystore_repo
    from hg_gateway.db import get_connection

    keystore_repo.social_account_create(
        social_account_id="acct-underling-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="underling-fourclaw",
        entity_scope="underling-chan",
        persona_scope="underling_chan_operational",
        state="verified",
        db_path=str(tmp_path / "gateway.sqlite3"),
    )
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'social_account', ?, 'post_proof', ?, ?, datetime('now', '-1 hours'))""",
            ("proof-budget-reset-1", "acct-underling-fourclaw", "memory/artifacts/social_accounts/post1.json", '{"status":"ok"}'),
        )

    entry = ScheduleEntry(
        job_id="social-media-underling",
        interval_minutes=15,
        inputs={"task_name": "fourclaw-engage", "workflow_id": "social-media"},
    )
    state = ScheduleState(entries=[entry], workspace_root=tmp_path)
    result = state.next_due(after=datetime.now(timezone.utc))
    assert result is not None
    due_time, _ = result
    delta_hours = (due_time - datetime.now(timezone.utc)).total_seconds() / 3600
    assert 22.5 <= delta_hours <= 23.5
