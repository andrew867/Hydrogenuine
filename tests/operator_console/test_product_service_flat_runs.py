import json
import sys
from pathlib import Path


_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from app.services import product_service


def test_get_run_hydrates_from_flat_dag_record(tmp_path, monkeypatch):
    run_id = "run-flat-123"
    dag_runs = tmp_path / "memory" / "automation" / "dag_runs"
    dag_runs.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "graph_id": "moltbook_auto_post_v1",
        "final_status": "completed",
        "state": {"budget_used": {"external_calls": 0}},
        "node_outputs": {
            "execute_task": {"result": {"status": "completed", "mode": "text_only"}},
            "read_content_queue": {"result": {"status": "completed", "live_read": True}},
        },
        "node_states": {
            "start_cycle": {"id": "start_cycle", "status": "done", "started_at": "2026-02-25T20:00:00Z"},
            "execute_task": {
                "id": "execute_task",
                "status": "failed",
                "started_at": "2026-02-25T20:00:02Z",
                "ended_at": "2026-02-25T20:00:03Z",
                "error": {"code": "TOOL_ERROR", "message": "network timeout"},
            },
        },
    }
    (dag_runs / f"{run_id}.json").write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(product_service, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(
        product_service,
        "_get_run",
        lambda rid: {
            "run_id": rid,
            "graph_id": "moltbook_auto_post_v1",
            "status": "completed",
            "started_at": 1.0,
            "ended_at": 2.0,
            "run_dir": str(tmp_path / ".missing-run-dir"),
        },
    )

    run = product_service.get_run(run_id)
    assert run is not None
    assert run["run_id"] == run_id
    assert run["audit_summary"]["final_status"] == "completed"
    assert run["audit_summary"]["execution"]["mode"] == "text_only"
    assert len(run["trace_timeline"]) >= 2
    execute_rows = [row for row in run["trace_timeline"] if row.get("node_id") == "execute_task"]
    assert execute_rows
    assert execute_rows[0].get("error", {}).get("code") == "TOOL_ERROR"


def test_list_run_artifacts_returns_flat_record_and_draft(tmp_path, monkeypatch):
    run_id = "run-flat-artifacts"
    dag_runs = tmp_path / "memory" / "automation" / "dag_runs"
    drafts = tmp_path / "memory" / "automation" / "automation-moltbook-auto-post" / "drafts"
    dag_runs.mkdir(parents=True, exist_ok=True)
    drafts.mkdir(parents=True, exist_ok=True)
    draft_path = drafts / "draft.json"
    draft_path.write_text("{\"draft\":true}", encoding="utf-8")
    payload = {
        "run_id": run_id,
        "graph_id": "moltbook_auto_post_v1",
        "node_outputs": {
            "execute_task": {"result": {"draft_artifact": str(draft_path)}},
        },
    }
    (dag_runs / f"{run_id}.json").write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(product_service, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(
        product_service,
        "_get_run",
        lambda rid: {
            "run_id": rid,
            "graph_id": "moltbook_auto_post_v1",
            "status": "completed",
            "started_at": 1.0,
            "ended_at": 2.0,
            "run_dir": str(tmp_path / ".missing-run-dir"),
        },
    )

    artifacts = product_service.list_run_artifacts(run_id)
    assert artifacts is not None
    names = {item["name"] for item in artifacts["items"]}
    assert f"{run_id}.json" in names
    assert any(name.replace("\\", "/").endswith("drafts/draft.json") for name in names)
