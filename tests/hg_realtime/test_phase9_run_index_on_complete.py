"""Phase 9: Run index on complete from run_dag_job."""

import gc
import json
import os
import tempfile
import time

import pytest


def test_update_run_index_on_complete():
    """update_run_index_on_complete reads summary.json and updates run index."""
    from hg_realtime.integrations.run_index_on_complete import update_run_index_on_complete
    from hg_realtime.integrations.run_index import SqliteRunIndexWriter

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "runs.db")
        run_dir = os.path.join(td, "run-abc")
        os.makedirs(run_dir, exist_ok=True)
        summary = {
            "run_id": "run-abc",
            "graph_id": "test-graph",
            "final_status": "cancelled",
            "started_at": time.time() - 10,
            "ended_at": time.time(),
        }
        with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f)

        # Ensure run exists in index (like launcher record_start)
        writer = SqliteRunIndexWriter(sqlite_path=db_path)
        writer.record_start(run_id="run-abc", workflow_id="test-graph", status="running", run_dir=run_dir)

        update_run_index_on_complete(run_dir, run_id="run-abc", db_path=db_path)

        record = writer.get_run("run-abc")
        assert record is not None
        assert record.status == "cancelled"
        assert record.ended_at is not None
        del writer
        gc.collect()
        time.sleep(0.05)


def test_update_run_index_on_complete_iso_ended_at():
    """ISO ended_at in summary.json is parsed correctly (not float()-cast)."""
    from hg_realtime.integrations.run_index_on_complete import update_run_index_on_complete
    from hg_realtime.integrations.run_index import SqliteRunIndexWriter

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "runs.db")
        run_dir = os.path.join(td, "run-iso")
        os.makedirs(run_dir, exist_ok=True)
        summary = {
            "run_id": "run-iso",
            "graph_id": "test-graph",
            "final_status": "completed",
            "started_at": "2026-06-11T04:43:07.121584Z",
            "ended_at": "2026-06-11T04:44:04.470737Z",
        }
        with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f)

        writer = SqliteRunIndexWriter(sqlite_path=db_path)
        writer.record_start(run_id="run-iso", workflow_id="test-graph", status="running", run_dir=run_dir)
        update_run_index_on_complete(run_dir, run_id="run-iso", db_path=db_path)

        record = writer.get_run("run-iso")
        assert record is not None
        assert record.status == "completed"
        assert record.ended_at is not None
        assert record.ended_at > 1_700_000_000
        del writer
        gc.collect()
        time.sleep(0.05)


def test_update_run_index_on_complete_db_path_none_uses_gateway_store(tmp_path, monkeypatch):
    """With db_path=None, completion is written to gateway store (single DB, no split brain)."""
    from hg_realtime.integrations.run_index_on_complete import update_run_index_on_complete
    from hg_realtime.integrations.run_index import default_run_index_writer, default_run_index_reader

    gateway_db = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    run_dir = tmp_path / "run-xyz"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text(
        json.dumps({
            "run_id": "run-xyz",
            "graph_id": "wf-one",
            "final_status": "completed",
            "started_at": time.time() - 5,
            "ended_at": time.time(),
        }),
        encoding="utf-8",
    )
    writer = default_run_index_writer()
    writer.record_start(run_id="run-xyz", workflow_id="wf-one", status="running", run_dir=str(run_dir))
    update_run_index_on_complete(run_dir, run_id="run-xyz", db_path=None)
    reader = default_run_index_reader()
    record = reader.get_run("run-xyz")
    assert record is not None
    assert record.status == "completed"
    assert record.ended_at is not None
