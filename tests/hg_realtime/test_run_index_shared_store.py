import os

from hg_realtime.integrations.run_index import default_run_index_reader, default_run_index_writer


def test_default_run_index_uses_gateway_store_with_sqlite_backend(tmp_path):
    db_path = tmp_path / "gateway.sqlite3"
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_db = os.environ.get("HG_GATEWAY_DB_PATH")
    try:
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = str(db_path)
        writer = default_run_index_writer()
        reader = default_run_index_reader()
        writer.record_start(
            run_id="run-shared-1",
            workflow_id="wf-1",
            correlation_id="corr-shared-1",
            run_dir=str(tmp_path / "runs" / "run-shared-1"),
        )
        row = reader.get_run("run-shared-1")
        assert row is not None
        assert row.workflow_id == "wf-1"
        assert row.correlation_id == "corr-shared-1"
        writer.record_completion(run_id="run-shared-1", status="completed", completed_ts=123.0)
        row2 = reader.get_run_by_correlation_id("corr-shared-1")
        assert row2 is not None
        assert row2.status == "completed"
        assert row2.ended_at == 123.0
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_db is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_db
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
