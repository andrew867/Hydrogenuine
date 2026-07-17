"""Tests for hg_core.wrappers.cron_health_monitor (Phase 1: never_run, memory-maintenance)."""

import pytest
from datetime import datetime, timezone

from hg_core.wrappers.cron_health_monitor import (
    check_job_health,
    EXPECTED_INTERVALS,
    MIN_VALID_LAST_RUN_MS,
    maybe_record_cron_disruption,
)
from hg_core.temporal_changelog import load_recent_temporal_events


def test_last_run_at_zero_returns_never_run():
    """lastRunAtMs 0 must return never_run, not overdue."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    job = {
        "id": "memory-maintenance",
        "enabled": True,
        "state": {"lastRunAtMs": 0, "lastStatus": "ok"},
        "schedule": {"kind": "every", "everyMs": 3600000},
    }
    result = check_job_health(job, now_ms)
    assert result["status"] == "never_run"
    assert result["message"] == "memory-maintenance has never run"
    assert "overdue" not in result.get("message", "").lower()


def test_last_run_at_none_returns_never_run():
    """lastRunAtMs missing (None) must return never_run."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    job = {
        "id": "some-job",
        "enabled": True,
        "state": {},
        "schedule": {"kind": "every", "everyMs": 3600000},
    }
    result = check_job_health(job, now_ms)
    assert result["status"] == "never_run"


def test_memory_maintenance_in_expected_intervals():
    """memory-maintenance must be in EXPECTED_INTERVALS so health check has a threshold."""
    assert "memory-maintenance" in EXPECTED_INTERVALS["every"]


def test_maybe_record_cron_disruption_only_for_major_unhealthy_jobs(tmp_path):
    summary = {
        "results": [
            {
                "job_id": "memory-maintenance",
                "workflow_label": "Memory maintenance",
                "enabled": True,
                "healthy": False,
                "status": "overdue",
                "overdue_by_ms": 7 * 60 * 60 * 1000,
            }
        ]
    }
    maybe_record_cron_disruption(summary, tmp_path)
    rows = load_recent_temporal_events(workspace_root=tmp_path, agent_id="agentchan", limit=10, days=30)
    assert rows
    assert rows[0]["title"] == "Scheduler disruption"
