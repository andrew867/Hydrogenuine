"""Tests for RunDirTraceStore."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hg_realtime.integrations.run_index import RunRecord

from hg_bridge.integrations.trace_store import RunDirTraceStore


def test_run_dir_trace_store_fetch_window_empty_when_no_run(tmp_path):
    """fetch_window returns [] when run index has no run for correlation_id."""
    reader = MagicMock()
    reader.get_run_by_correlation_id.return_value = None
    store = RunDirTraceStore(reader)
    assert store.fetch_window(correlation_id="no-such", start_ts=0.0, end_ts=time.time()) == []


def test_run_dir_trace_store_fetch_window_empty_when_no_run_dir(tmp_path):
    """fetch_window returns [] when run has no run_dir."""
    reader = MagicMock()
    reader.get_run_by_correlation_id.return_value = RunRecord(
        run_id="r1",
        workflow_id="w1",
        status="completed",
        started_at=0.0,
        ended_at=100.0,
        run_dir=None,
        correlation_id="c1",
    )
    store = RunDirTraceStore(reader)
    assert store.fetch_window(correlation_id="c1", start_ts=0.0, end_ts=200.0) == []


def test_run_dir_trace_store_fetch_window_from_events_jsonl(tmp_path):
    """fetch_window reads events.jsonl and returns StepTrace list."""
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()
    events_path = run_dir / "events.jsonl"
    now_ts = time.time()
    events_path.write_text(
        json.dumps({
            "timestamp": "2025-01-15T12:00:00Z",
            "event": "dag_run_started",
            "graph_id": "g1",
            "run_id": "run-1",
        }) + "\n"
        + json.dumps({
            "timestamp": "2025-01-15T12:00:01Z",
            "event": "dag_node_completed",
            "graph_id": "g1",
            "run_id": "run-1",
            "node_id": "n1",
            "status": "done",
        }) + "\n",
        encoding="utf-8",
    )
    # Use timestamps that include the parsed event times (2025-01-15 12:00:00 UTC)
    from datetime import datetime, timezone
    start_ts = datetime(2025, 1, 15, 11, 59, 0, tzinfo=timezone.utc).timestamp()
    end_ts = datetime(2025, 1, 15, 12, 2, 0, tzinfo=timezone.utc).timestamp()

    reader = MagicMock()
    reader.get_run_by_correlation_id.return_value = RunRecord(
        run_id="run-1",
        workflow_id="g1",
        status="completed",
        started_at=start_ts,
        ended_at=end_ts,
        run_dir=str(run_dir),
        correlation_id="corr-1",
    )
    store = RunDirTraceStore(reader)
    steps = store.fetch_window(correlation_id="corr-1", start_ts=start_ts, end_ts=end_ts)
    assert len(steps) >= 1
    assert steps[0].correlation_id == "corr-1"
    assert steps[0].run_id == "run-1"
    assert steps[0].node_id in ("run", "n1")


def test_run_dir_trace_store_integration_real_run_index(tmp_path):
    """Integration: real SqliteRunIndexWriter + fixture run_dir with events.jsonl; fetch_window returns non-empty list."""
    from hg_realtime.integrations.run_index import SqliteRunIndexWriter
    from datetime import datetime, timezone

    run_id = "run-int-1"
    corr = "corr-int-1"
    run_dir = tmp_path / "dag_runs" / "job1" / run_id
    run_dir.mkdir(parents=True)
    events_path = run_dir / "events.jsonl"
    start_ts = datetime(2025, 2, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    end_ts = datetime(2025, 2, 1, 10, 5, 0, tzinfo=timezone.utc).timestamp()
    events_path.write_text(
        json.dumps({
            "timestamp": "2025-02-01T10:01:00Z",
            "event": "dag_node_completed",
            "graph_id": "job1",
            "run_id": run_id,
            "node_id": "n1",
            "status": "done",
        }) + "\n",
        encoding="utf-8",
    )

    db_path = str(tmp_path / "runs.db")
    run_index = SqliteRunIndexWriter(sqlite_path=db_path)
    run_index.record_start(
        run_id=run_id,
        workflow_id="job1",
        job_id="job1",
        status="completed",
        correlation_id=corr,
        run_dir=str(run_dir),
    )
    run_index.record_completion(run_id=run_id, status="completed", completed_ts=end_ts)

    store = RunDirTraceStore(run_index)
    steps = store.fetch_window(correlation_id=corr, start_ts=start_ts, end_ts=end_ts)
    assert len(steps) >= 1
    assert steps[0].correlation_id == corr
    assert steps[0].run_id == run_id
    assert steps[0].node_id == "n1"


def test_run_dir_trace_store_falls_back_to_run_times_when_events_have_no_timestamp(tmp_path):
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()
    events_path = run_dir / "events.jsonl"
    start_ts = 1773012474.0
    end_ts = 1773013374.0
    events_path.write_text(
        json.dumps(
            {
                "event": "dag_run_started",
                "graph_id": "g1",
                "run_id": "run-1",
            }
        )
        + "\n"
        + json.dumps(
            {
                "event": "dag_node_completed",
                "graph_id": "g1",
                "run_id": "run-1",
                "node_id": "n1",
                "status": "done",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    reader = MagicMock()
    reader.get_run_by_correlation_id.return_value = RunRecord(
        run_id="run-1",
        workflow_id="g1",
        status="completed",
        started_at=start_ts,
        ended_at=end_ts,
        run_dir=str(run_dir),
        correlation_id="corr-1",
    )
    store = RunDirTraceStore(reader)
    steps = store.fetch_window(correlation_id="corr-1", start_ts=start_ts - 1, end_ts=end_ts + 1)
    assert len(steps) == 2
    assert all(step.ts >= start_ts for step in steps)
