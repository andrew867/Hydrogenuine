"""Phase 5 DAG studio: save validation and backup."""

from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"


def _minimal_valid_dag():
    return {
        "graph_id": "phase5_test_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast"},
        "inputs": {},
        "nodes": [
            {
                "id": "a",
                "type": "tool",
                "assigned_entity": "stub",
                "depends_on": [],
                "inputs": {},
                "outputs": {},
                "policy": {"timeout_s": 300, "max_retries": 0},
                "checkpoints": {"before": False, "after": False},
            },
        ],
    }


def test_save_scheduled_dag_validates_and_backs_up(tmp_path):
    """Save validates DAG and creates backup before overwrite."""
    import sys
    if not _server_path.exists():
        pytest.skip("operator_console/server not found")
    if str(_server_path) not in sys.path:
        sys.path.insert(0, str(_server_path))
    from app.services.scheduled_jobs_service import save_scheduled_dag, SCHEDULED_JOB_TO_DAG

    job_id = "fourclaw-auto-post-cadence"
    rel = SCHEDULED_JOB_TO_DAG.get(job_id)
    assert rel
    dag_path = tmp_path / rel
    dag_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _minimal_valid_dag()
    existing["graph_id"] = "fourclaw_auto_post_v1"
    dag_path.write_text('{"graph_id":"x","nodes":[]}', encoding="utf-8")

    result = save_scheduled_dag(tmp_path, job_id, existing)
    assert result.get("saved") is True
    assert result.get("backup_path")
    assert ".bak-" in result["backup_path"]
    backup_abs = Path(result["backup_path"])
    assert backup_abs.exists()


def test_save_scheduled_dag_rejects_invalid(tmp_path):
    """Save raises when DAG validation fails."""
    import sys
    if not _server_path.exists():
        pytest.skip("operator_console/server not found")
    if str(_server_path) not in sys.path:
        sys.path.insert(0, str(_server_path))
    from app.services.scheduled_jobs_service import save_scheduled_dag

    invalid = {
        "graph_id": "x",
        "nodes": [{"id": "n1", "type": "tool", "depends_on": []}],
    }
    with pytest.raises(ValueError) as exc:
        save_scheduled_dag(tmp_path, "fourclaw-auto-post-cadence", invalid)
    assert "INVALID_DAG" in str(exc.value) or "errors" in str(exc.value)
