import json
import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from app.services import run_index_db
    from app.services.run_index_db import backfill_discovered_runs, list_runs
else:
    run_index_db = None
    list_runs = None


@pytest.mark.skipif(list_runs is None, reason="operator_console/server not found")
def test_list_runs_includes_discovered_dag_run_dirs(tmp_path, monkeypatch):
    workspace = tmp_path
    gateway_db = tmp_path / "gateway.sqlite3"
    dag_run_dir = workspace / "memory" / "automation" / "dag_runs" / "workflow-a" / "run_20260225T120000Z_abc12345"
    dag_run_dir.mkdir(parents=True)
    (dag_run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": "run_20260225T120000Z_abc12345",
                "graph_id": "workflow-a",
                "final_status": "completed",
                "started_at": 1700000000.0,
                "ended_at": 1700000020.0,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_index_db.settings, "runs_root", str(tmp_path / ".hg_runs"))
    monkeypatch.setattr(run_index_db, "_workspace_root", lambda: workspace)
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    monkeypatch.delenv("HG_DISABLE_RUN_DISCOVERY", raising=False)

    backfill_discovered_runs(limit=5000)
    rows = list_runs(limit=5000)
    ids = {row.get("run_id") for row in rows}
    assert "run_20260225T120000Z_abc12345" in ids

    row = run_index_db.get_run("run_20260225T120000Z_abc12345")
    assert row is not None
    assert row.get("graph_id") == "workflow-a"


@pytest.mark.skipif(list_runs is None, reason="operator_console/server not found")
def test_list_runs_ignores_placeholder_flat_files(tmp_path, monkeypatch):
    workspace = tmp_path
    gateway_db = tmp_path / "gateway.sqlite3"
    dag_runs_root = workspace / "memory" / "automation" / "dag_runs"
    dag_runs_root.mkdir(parents=True)
    (dag_runs_root / "bad-placeholder.json").write_text(
        json.dumps(
            {
                "run_id": "run_id",
                "graph_id": "graph_id",
                "status": "status",
                "started_at": "started_at",
                "ended_at": "ended_at",
                "run_dir": "run_dir",
            }
        ),
        encoding="utf-8",
    )
    (dag_runs_root / "good-run.json").write_text(
        json.dumps(
            {
                "run_id": "good-run",
                "graph_id": "workflow-good",
                "status": "completed",
                "started_at": 1700001000.0,
                "ended_at": 1700001010.0,
                "run_dir": str(dag_runs_root / "good-run"),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_index_db.settings, "runs_root", str(tmp_path / ".hg_runs"))
    monkeypatch.setattr(run_index_db, "_workspace_root", lambda: workspace)
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(gateway_db))
    monkeypatch.delenv("HG_DISABLE_RUN_DISCOVERY", raising=False)

    backfill_discovered_runs(limit=5000)
    rows = list_runs(limit=5000)
    ids = {row.get("run_id") for row in rows}
    assert "good-run" in ids
    assert "run_id" not in ids


@pytest.mark.skipif(run_index_db is None, reason="operator_console/server not found")
def test_row_to_dict_handles_dict_like_postgres_rows():
    class FakeRow(dict):
        pass

    row = FakeRow(run_id="real-run", graph_id="workflow-real", status="completed")
    data = run_index_db._row_to_dict(row)
    assert data == {
        "run_id": "real-run",
        "graph_id": "workflow-real",
        "status": "completed",
    }
