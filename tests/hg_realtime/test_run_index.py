"""Run index writer and reader tests."""

import gc
import os
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from hg_realtime.integrations.run_index import SqliteRunIndexWriter, RunRecord


def test_sqlite_run_index_record_start():
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        os.close(fd)
        writer = SqliteRunIndexWriter(sqlite_path=path)
        writer.record_start(
            run_id="run-123",
            workflow_id="fourclaw-auto-post-cadence",
            job_id="fourclaw-auto-post-cadence",
            status="running",
            correlation_id="corr-1",
            run_dir=str(Path(path).parent / "dag_runs" / "fourclaw-auto-post-cadence" / "run-123"),
        )
        del writer
        gc.collect()
        time.sleep(0.05)
        with sqlite3.connect(path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT run_id, graph_id, status, run_dir FROM runs WHERE run_id=?", ("run-123",)).fetchone()
        assert row is not None
        assert row["run_id"] == "run-123"
        assert row["graph_id"] == "fourclaw-auto-post-cadence"
        assert row["status"] == "running"
        assert "run-123" in (row["run_dir"] or "")
    finally:
        try:
            Path(path).unlink(missing_ok=True)
        except PermissionError:
            pass


def test_sqlite_run_index_record_completion_get_run_get_by_correlation_id(tmp_path):
    db_path = str(tmp_path / "runs.db")
    writer = SqliteRunIndexWriter(sqlite_path=db_path)
    run_dir = str(tmp_path / "dag_runs" / "job1" / "run-456")
    writer.record_start(
        run_id="run-456",
        workflow_id="job1",
        job_id="job1",
        status="running",
        correlation_id="corr-abc",
        run_dir=run_dir,
    )
    r = writer.get_run("run-456")
    assert r is not None
    assert r.run_id == "run-456"
    assert r.workflow_id == "job1"
    assert r.correlation_id == "corr-abc"
    assert r.run_dir == run_dir
    assert r.ended_at is None

    by_corr = writer.get_run_by_correlation_id("corr-abc")
    assert by_corr is not None
    assert by_corr.run_id == "run-456"

    writer.record_completion(run_id="run-456", status="completed", completed_ts=12345.0)
    r2 = writer.get_run("run-456")
    assert r2 is not None
    assert r2.status == "completed"
    assert r2.ended_at == 12345.0

    assert writer.get_run("nonexistent") is None
    assert writer.get_run_by_correlation_id("no-such-corr") is None


def test_sqlite_run_index_record_start_pending_approval_and_blocked_reason(tmp_path):
    """record_start with status pending_approval stores blocked_reason and pending_request_json."""
    db_path = str(tmp_path / "runs.db")
    writer = SqliteRunIndexWriter(sqlite_path=db_path)
    pending_request = {"workflow_id": "wf1", "tenant_id": "t1", "actor_id": "a1", "correlation_id": "c1", "resolved_inputs": {}}
    import json
    writer.record_start(
        run_id="run-pending-1",
        workflow_id="wf1",
        status="pending_approval",
        correlation_id="c1",
        run_dir=None,
        blocked_reason="blocked by release gate",
        pending_request_json=json.dumps(pending_request),
    )
    r = writer.get_run("run-pending-1")
    assert r is not None
    assert r.status == "pending_approval"
    assert r.run_dir is None
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT run_id, status, blocked_reason, pending_request_json FROM runs WHERE run_id=?", ("run-pending-1",)).fetchone()
    assert row is not None
    assert row["status"] == "pending_approval"
    assert "release gate" in (row["blocked_reason"] or "")
    payload = json.loads(row["pending_request_json"] or "{}")
    assert payload.get("workflow_id") == "wf1"
