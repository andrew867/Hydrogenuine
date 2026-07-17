"""Realtime schedule must cover all production DAG registry jobs (demo heartbeat path)."""

import json
import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[1]
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

from scripts.dag_runtime_jobs import DAG_JOB_REGISTRY

# Test-only or invoked via social-media alias entries — not required as standalone timer rows.
_SCHEDULE_EXEMPT = frozenset(
    {
        "phase10-smoke",
        "social-media",
    }
)


def _scheduled_job_ids() -> set[str]:
    path = _workspace / "memory" / "automation" / "realtime_schedule.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {str(e["job_id"]) for e in entries if isinstance(e, dict) and e.get("job_id")}


def test_realtime_schedule_covers_production_registry():
    scheduled = _scheduled_job_ids()
    missing = sorted(
        job_id
        for job_id in DAG_JOB_REGISTRY.keys()
        if job_id not in _SCHEDULE_EXEMPT and job_id not in scheduled
    )
    assert not missing, f"realtime_schedule.json missing production jobs: {missing}"


def test_realtime_schedule_entries_have_timing():
    path = _workspace / "memory" / "automation" / "realtime_schedule.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("job_id"):
            continue
        cron = entry.get("cron")
        interval = entry.get("interval_minutes")
        assert cron or interval, f"job {entry['job_id']} needs cron or interval_minutes"
        assert not (cron and interval), f"job {entry['job_id']} must not set both cron and interval"
