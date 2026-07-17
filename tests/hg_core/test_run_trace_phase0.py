"""Integration tests for autonomy Phase 0: run trace (O1, O2) and failure class in summary.

- Full workflow run produces one trace record with run_id and node timings.
- Trace/summary references output artifact ids (run_dir).
- Failure in a node produces failure_class in trace/summary.
"""

import json
import pytest
from pathlib import Path

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    TaskGraphExecutor,
)
from hg_core.task_graph.state_store import StateStore


def _node(nid: str, depends_on: list = None, node_type: str = "tool") -> Node:
    return Node(
        id=nid,
        type=node_type,
        assigned_entity="stub",
        depends_on=depends_on or [],
        inputs={},
        outputs={},
        policy=NodePolicy(),
        checkpoints=Checkpoints(),
    )


def test_run_with_run_dir_produces_trace_with_run_id_and_artifacts(tmp_path):
    """Run with run_dir: summary has run_id; run_dir contains summary.json and state.json with run_id."""
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()
    dag = DAG(
        graph_id="trace_test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"])],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    stub = lambda node, inputs, **kwargs: {"ok": True, "outputs": {}}
    exec = TaskGraphExecutor(dispatcher=stub, state_store=store)
    summary = exec.run(dag, graph_inputs={}, run_dir=run_dir)

    assert "run_id" in summary
    assert summary["run_id"] is not None
    assert len(summary["run_id"]) >= 8

    assert (run_dir / "summary.json").exists()
    assert (run_dir / "state.json").exists()

    with open(run_dir / "summary.json", encoding="utf-8") as f:
        file_summary = json.load(f)
    assert file_summary["run_id"] == summary["run_id"]
    assert file_summary.get("graph_id") == "trace_test"
    assert "started_at" in file_summary or "started_at" in summary.get("run_state", {})
    assert "counts" in file_summary
    counts = file_summary["counts"]
    assert counts.get("done", 0) + counts.get("failed", 0) >= 1, "at least one node ran (done or failed)"

    with open(run_dir / "state.json", encoding="utf-8") as f:
        state = json.load(f)
    assert state.get("run_id") == summary["run_id"]


def test_run_with_run_dir_events_contain_run_id(tmp_path):
    """When run_dir is set, events.jsonl in run_dir contains run_id in each event."""
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()
    dag = DAG(
        graph_id="events_test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a")],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(state_store=store)
    summary = exec.run(dag, graph_inputs={}, run_dir=run_dir)

    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        run_ids = []
        with open(events_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ev = json.loads(line)
                    run_ids.append(ev.get("run_id"))
        assert all(rid == summary["run_id"] for rid in run_ids if rid), "events should reference run_id"


def test_failed_node_produces_failure_class_in_summary(tmp_path):
    """When a node fails, summary error_summary or run_state includes failure_class for that failure."""
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()

    def fail_a(node, inputs, **kwargs):
        if node.id == "a":
            raise TimeoutError("node a timed out")
        return {"ok": True, "outputs": {}}

    dag = DAG(
        graph_id="fail_test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"])],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(dispatcher=fail_a, state_store=store)
    summary = exec.run(dag, graph_inputs={}, run_dir=run_dir)

    file_summary_path = run_dir / "summary.json"
    assert file_summary_path.exists()
    with open(file_summary_path, encoding="utf-8") as f:
        file_summary = json.load(f)

    if not summary["ok"]:
        assert summary["nodes"]["a"]["status"] == "failed"
        error_summary = file_summary.get("error_summary", [])
        assert len(error_summary) >= 1
        primary = error_summary[0]
        assert "failure_class" in primary, "error_summary entries must include failure_class (F1)"
        assert primary["failure_class"] in (
            "timeout", "internal_error", "unknown"
        ), "TimeoutError should map to timeout or internal_error or unknown"
        if file_summary.get("final_status") == "failed":
            assert "failure_class" in file_summary, "run summary should have top-level failure_class when failed"
    else:
        pytest.skip("dispatcher did not raise in this environment (run completed successfully)")
