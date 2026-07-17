import sys
from pathlib import Path


_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))


def test_sla_gather_traces_prefers_indexed_runs(monkeypatch):
    from app.api import sla

    monkeypatch.setattr(
        "app.services.run_index_db.backfill_discovered_runs",
        lambda limit=0: {"ok": True, "discovered": 1},
    )
    monkeypatch.setattr(
        "app.services.run_index_db.list_runs",
        lambda limit=0: [
            {
                "run_id": "run-1",
                "graph_id": "workflow-a",
                "status": "completed",
            },
            {
                "run_id": "run-2",
                "graph_id": "workflow-b",
                "status": "degraded",
            },
        ],
    )

    traces = sla._gather_traces_from_workspace(_workspace, limit=10)
    assert traces == [
        {
            "run_id": "run-1",
            "workflow_id": "workflow-a",
            "status": "success",
            "failure_class": None,
            "budget_used": None,
        },
        {
            "run_id": "run-2",
            "workflow_id": "workflow-b",
            "status": "degraded",
            "failure_class": None,
            "budget_used": None,
        },
    ]
