"""
E2E acceptance test (plan x1): golden fixture + fake destination; assert structure, dedupe, budget, no side effects.

Runs a DAG with fourclaw-auto-post node and mocked dispatch (no real post). Asserts:
- Output structure (ok, run_id, node_outputs, graph_id).
- Dedupe: posting_dedupe check_already_posted/record_posted contract (unit tests cover this).
- Budget: summary has run_id and expected keys.
- No side effects in test: dispatch is mocked so no real API call.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from hg_core.task_graph import load_dag, TaskGraphExecutor, StateStore


def test_e2e_dag_run_structure_and_no_side_effects(tmp_path):
    """Run a minimal DAG with fourclaw-auto-post; dispatch mocked so no real post. Assert structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".hg").touch()
    dags = workspace / "memory" / "automation" / "dags"
    dags.mkdir(parents=True)
    dag_json = {
        "graph_id": "e2e_test_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast"},
        "inputs": {"goal": ""},
        "nodes": [
            {
                "id": "post",
                "type": "agent",
                "assigned_entity": "fourclaw-auto-post",
                "depends_on": [],
                "inputs": {"goal": "$graph.inputs.goal"},
                "outputs": {"result": {}},
                "policy": {"timeout_s": 5, "max_retries": 0},
            }
        ],
    }
    dag_file = dags / "e2e_test.json"
    dag_file.write_text(json.dumps(dag_json))
    dag = load_dag(dag_file)

    def fake_dispatch(*args, **kwargs):
        return {"ok": True, "outputs": {"thread_id": "fake-1", "thread_url": "https://example.com/t/fake-1"}}

    run_dir = workspace / "memory" / "automation" / "dag_runs" / "e2e_run"
    run_dir.mkdir(parents=True)
    base = run_dir.parent

    with patch("hg_core.task_graph.dispatch.dispatch_agent", side_effect=fake_dispatch):
        with patch("hg_lib.config.get_workspace_root", return_value=workspace):
            store = StateStore(base_dir=base)
            executor = TaskGraphExecutor(state_store=store)
            summary = executor.run(dag, graph_inputs={"goal": "E2E test goal"}, run_dir=run_dir)

    assert summary.get("ok") is True
    assert "run_id" in summary
    assert "graph_id" in summary
    assert summary.get("graph_id") == "e2e_test_v1"
    assert "node_outputs" in summary
    assert "post" in summary.get("node_outputs", {})
    assert (run_dir / "summary.json").exists()
    summary_file = json.loads((run_dir / "summary.json").read_text())
    assert summary_file.get("run_id") == summary.get("run_id")
    assert "run_id" in summary_file
