"""Test that run completion records to run index and publishes RUN_COMPLETED to bus."""

import json
import tempfile
import threading
from unittest.mock import MagicMock

import pytest

from hg_realtime.integrations.dag_launcher import (
    RUN_COMPLETED_KIND,
    _publish_run_completed,
    _RunMeta,
)


def test_publish_run_completion_calls_record_completion_and_publishes_event():
    """_publish_run_completed records completion and publishes one RUN_COMPLETED event to bus."""
    published = []

    class MockBus:
        def publish(self, ev):
            published.append(ev)

    mock_run_index = MagicMock()
    run_meta = {"run-1": _RunMeta(
        correlation_id="corr-xyz",
        tenant_id="tenant1",
        actor_id="agent1",
        workflow_id="wf1",
        started_ts=1000.0,
        run_dir="/tmp/run-1",
    )}
    lock = threading.Lock()

    _publish_run_completed(
        run_index=mock_run_index,
        bus=MockBus(),
        run_meta=run_meta,
        lock=lock,
        run_id="run-1",
        returncode=0,
    )

    mock_run_index.record_completion.assert_called_once()
    call_kw = mock_run_index.record_completion.call_args[1]
    assert call_kw["run_id"] == "run-1"
    assert call_kw["status"] == "completed"
    assert call_kw["completed_ts"] > 0

    assert len(published) == 1
    ev = published[0]
    assert ev.payload.get("kind") == RUN_COMPLETED_KIND
    assert ev.payload.get("correlation_id") == "corr-xyz"
    assert ev.payload.get("run_id") == "run-1"
    assert ev.payload.get("tenant_id") == "tenant1"
    assert ev.payload.get("status") == "completed"
    assert ev.correlation_id == "corr-xyz"

    assert "run-1" not in run_meta


def test_publish_run_completion_no_bus_no_record_completion_if_no_meta():
    """If run_meta has no entry for run_id, nothing is called."""
    mock_run_index = MagicMock()
    run_meta = {}
    lock = threading.Lock()
    published = []

    class MockBus:
        def publish(self, ev):
            published.append(ev)

    _publish_run_completed(
        run_index=mock_run_index,
        bus=MockBus(),
        run_meta=run_meta,
        lock=lock,
        run_id="run-missing",
        returncode=0,
    )

    mock_run_index.record_completion.assert_not_called()
    assert len(published) == 0


def test_publish_run_completion_prefers_summary_final_status_over_returncode():
    """Cancelled/failed in summary.json wins over subprocess returncode."""
    with tempfile.TemporaryDirectory() as td:
        run_dir = f"{td}/run-cancel"
        import os

        os.makedirs(run_dir, exist_ok=True)
        with open(f"{run_dir}/summary.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": "run-cancel",
                    "final_status": "cancelled",
                    "ended_at": "2026-06-11T04:36:22.720741Z",
                },
                f,
            )

        mock_run_index = MagicMock()
        run_meta = {
            "run-cancel": _RunMeta(
                correlation_id="corr-cancel",
                tenant_id="tenant1",
                actor_id="agent1",
                workflow_id="wf1",
                started_ts=1000.0,
                run_dir=run_dir,
            )
        }
        lock = threading.Lock()

        _publish_run_completed(
            run_index=mock_run_index,
            bus=None,
            run_meta=run_meta,
            lock=lock,
            run_id="run-cancel",
            returncode=1,
        )

        call_kw = mock_run_index.record_completion.call_args[1]
        assert call_kw["status"] == "cancelled"
        assert call_kw["completed_ts"] > 1_700_000_000
