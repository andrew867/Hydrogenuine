"""Realtime schedule must wake auto-post jobs without OpenClaw cron."""

import json
from pathlib import Path


def test_realtime_schedule_includes_auto_post_jobs():
    path = Path(__file__).resolve().parents[1] / "memory" / "automation" / "realtime_schedule.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    job_ids = {e.get("job_id") for e in entries if isinstance(e, dict)}
    assert "moltbook-auto-post" in job_ids
    assert "fourclaw-auto-post-cadence" in job_ids
    molt = next(e for e in entries if e.get("job_id") == "moltbook-auto-post")
    four = next(e for e in entries if e.get("job_id") == "fourclaw-auto-post-cadence")
    assert int(molt.get("interval_minutes") or 0) >= 10
    assert int(four.get("interval_minutes") or 0) >= 10
