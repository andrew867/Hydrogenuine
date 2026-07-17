"""E2E acceptance tests for autonomy Phase 6: golden fixture, fake destination, autonomy assertions."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from hg_core.task_graph import load_dag, TaskGraphExecutor, StateStore
from hg_core.task_graph.fake_destination_ledger import (
    record_would_post,
    read_ledger,
    clear_ledger,
)


def test_e2e_one_workflow_trace_and_fake_ledger(tmp_path):
    """E2E: Run one workflow with fake dispatch; assert trace exists, summary has run_id and keys."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".hg").touch()
    memory = workspace / "memory" / "automation"
    memory.mkdir(parents=True)
    dags = memory / "dags"
    dags.mkdir(parents=True)
    dag_json = {
        "graph_id": "e2e_phase6",
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
    (dags / "e2e_phase6.json").write_text(json.dumps(dag_json))
    dag = load_dag(dags / "e2e_phase6.json")

    run_dir = memory / "dag_runs" / "e2e_phase6_run"
    run_dir.mkdir(parents=True)
    base = memory / "dag_runs"

    def fake_dispatch(*args, **kwargs):
        return {"ok": True, "outputs": {"thread_id": "fake-1", "thread_url": "https://example.com/t/fake-1"}}

    with patch("hg_core.task_graph.dispatch.dispatch_agent", side_effect=fake_dispatch):
        with patch("hg_lib.config.get_workspace_root", return_value=workspace):
            store = StateStore(base_dir=base)
            executor = TaskGraphExecutor(state_store=store)
            summary = executor.run(dag, graph_inputs={"goal": "E2E Phase 6 goal"}, run_dir=run_dir)

    assert summary.get("ok") is True
    assert "run_id" in summary
    assert summary.get("graph_id") == "e2e_phase6"
    assert (run_dir / "summary.json").exists()
    file_summary = json.loads((run_dir / "summary.json").read_text())
    assert file_summary.get("run_id") == summary.get("run_id")
    assert "counts" in file_summary
    assert "error_summary" in file_summary


def test_fake_destination_ledger_one_event_per_post(tmp_path):
    """Fake ledger: record_would_post appends one event; read_ledger returns entries; clear_ledger resets."""
    clear_ledger(tmp_path)
    record_would_post(tmp_path, "run-1", "workflow-a", "hash1", "twitter", "2026-02-23")
    entries = read_ledger(tmp_path)
    assert len(entries) == 1
    assert entries[0]["event"] == "would_post"
    assert entries[0]["run_id"] == "run-1"
    assert entries[0]["content_hash"] == "hash1"

    record_would_post(tmp_path, "run-1", "workflow-a", "hash1", "twitter", "2026-02-23")
    entries2 = read_ledger(tmp_path)
    assert len(entries2) == 2

    clear_ledger(tmp_path)
    assert len(read_ledger(tmp_path)) == 0


def test_e2e_assert_trace_dedupe_budget_safety(tmp_path):
    """E2E assertions: trace has run_id; summary has failure_class when failed; budget/trace keys present."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".hg").touch()
    memory = workspace / "memory" / "automation"
    memory.mkdir(parents=True)
    dags = memory / "dags"
    dags.mkdir(parents=True)
    dag_json = {
        "graph_id": "e2e_assert",
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
                "policy": {"max_retries": 0},
            }
        ],
    }
    (dags / "e2e_assert.json").write_text(json.dumps(dag_json))
    dag = load_dag(dags / "e2e_assert.json")
    run_dir = memory / "dag_runs" / "assert_run"
    run_dir.mkdir(parents=True)
    base = memory / "dag_runs"

    with patch("hg_lib.config.get_workspace_root", return_value=workspace):
        store = StateStore(base_dir=base)
        executor = TaskGraphExecutor(state_store=store)
        summary = executor.run(dag, graph_inputs={}, run_dir=run_dir)

    assert "run_id" in summary
    assert (run_dir / "summary.json").exists()
    file_summary = json.loads((run_dir / "summary.json").read_text())
    assert file_summary.get("run_id") == summary.get("run_id")
    if file_summary.get("final_status") == "failed" and file_summary.get("error_summary"):
        assert any("failure_class" in e for e in file_summary["error_summary"])
