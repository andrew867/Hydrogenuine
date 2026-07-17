"""F4: Cron jobs must invoke DAG-native run_dag_job.py, not deprecated run_task.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _find_cron_jobs() -> Path | None:
    workspace = Path(__file__).resolve().parents[1]
    candidates = [
        workspace.parent / "cron" / "jobs.json",
        workspace / "cron" / "jobs.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def test_cron_jobs_use_run_dag_job():
    jobs_file = _find_cron_jobs()
    if jobs_file is None:
        pytest.skip("cron/jobs.json not found")
    data = json.loads(jobs_file.read_text(encoding="utf-8"))
    jobs = data.get("jobs") if isinstance(data, dict) else data
    assert isinstance(jobs, list), "expected jobs list"
    for job in jobs:
        payload = job.get("payload") or {}
        msg = payload.get("message") or job.get("message") or ""
        if "run_task.py" in msg and "run_dag_job.py" not in msg:
            raise AssertionError(f"Job {job.get('id')} still references deprecated run_task.py")
        if "fourclaw-engage.py" in msg or "moltbook-engage.py" in msg:
            raise AssertionError(f"Job {job.get('id')} references removed single-file script")
