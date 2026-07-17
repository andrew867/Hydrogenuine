"""Tests for hg_core.run_dag CLI and resume."""

import json
from pathlib import Path
from unittest.mock import patch

from hg_core.task_graph import DAG, Node, RunPolicy, NodePolicy, Checkpoints, TaskGraphExecutor
from hg_core.task_graph.state_store import StateStore, RunState


def _node(nid: str, depends_on: list = None) -> Node:
    return Node(
        id=nid,
        type="tool",
        assigned_entity="stub",
        depends_on=depends_on or [],
        inputs={},
        outputs={},
        policy=NodePolicy(),
        checkpoints=Checkpoints(),
    )


def test_resume_run_id_not_found(tmp_path: Path) -> None:
    """When --resume is used with a run_id that has no persisted state, resume returns ok False and error run_not_found."""
    dag_path = tmp_path / "dag.json"
    dag = DAG(
        graph_id="resume_test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a")],
    )
    dag_path.write_text(json.dumps(dag.to_dict(), indent=2))
    store = StateStore(base_dir=tmp_path / "runs")
    executor = TaskGraphExecutor(state_store=store)
    summary = executor.resume(dag, "nonexistent-run-id-12345")
    assert summary.get("ok") is False
    assert summary.get("error") == "run_not_found"
    assert summary.get("run_id") == "nonexistent-run-id-12345"


def test_resume_continues_run(tmp_path: Path) -> None:
    """Run a DAG with run_dir, then resume by run_id; resume completes and final_status is completed."""
    def stub_dispatcher(_node: Node, _inputs: dict) -> dict:
        return {"ok": True, "outputs": {}}

    dag_path = tmp_path / "dag.json"
    dag = DAG(
        graph_id="resume_continue",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"])],
    )
    dag_path.write_text(json.dumps(dag.to_dict(), indent=2))
    run_dir = tmp_path / "runs" / "my_run"
    run_dir.mkdir(parents=True)
    base_dir = run_dir.parent
    store = StateStore(base_dir=base_dir)
    executor = TaskGraphExecutor(
        state_store=store,
        dispatcher=stub_dispatcher,
        telemetry=lambda _name, _payload: None,
    )
    # Skip stakes gating so dispatch is allowed (test focuses on resume, not ledger)
    with patch("hg_core.task_graph.executor._ledger_workspace_root", return_value=None):
        summary = executor.run(dag, run_dir=run_dir)
    assert summary.get("ok") is True
    run_id = summary.get("run_id")
    assert run_id is not None
    with patch("hg_core.task_graph.executor._ledger_workspace_root", return_value=None):
        summary2 = executor.resume(dag, run_id, run_dir=run_dir)
    assert summary2.get("ok") is True
    assert summary2.get("final_status") in ("completed", "partial")
    assert summary2.get("run_id") == run_id


def test_state_store_default_base_dir_uses_workspace_root(tmp_path: Path) -> None:
    """When base_dir is None, StateStore uses get_workspace_root() / memory / automation / dag_runs (not cwd)."""
    try:
        import hg_lib.config  # noqa: F401
        target = "hg_lib.config.get_workspace_root"
    except ImportError:
        target = "hg_core.task_graph.state_store.get_workspace_root"
    with patch(target, return_value=tmp_path):
        from hg_core.task_graph.state_store import _default_base_dir, StateStore
        expected = tmp_path / "memory" / "automation" / "dag_runs"
        assert _default_base_dir() == expected
        store = StateStore(base_dir=None)
        assert store.base_dir == tmp_path / "memory" / "automation" / "dag_runs"
    # Save/load works with that path (persist under workspace root, not cwd)
    (tmp_path / "memory" / "automation" / "dag_runs").mkdir(parents=True)
    run_state = RunState(
        run_id="ws-root-test",
        graph_id="g1",
        started_at="2020-01-01T00:00:00Z",
        updated_at="2020-01-01T00:00:00Z",
        node_outputs={},
        node_states={},
    )
    from hg_core.task_graph.schema import Node as SchemaNode, NodePolicy, Checkpoints
    node = SchemaNode(
        id="a",
        type="tool",
        assigned_entity="stub",
        depends_on=[],
        inputs={},
        outputs={},
        policy=NodePolicy(),
        checkpoints=Checkpoints(),
    )
    with patch(target, return_value=tmp_path):
        store = StateStore(base_dir=None)
        store.save(run_state, [node])
        loaded = store.load("ws-root-test")
    assert loaded is not None
    assert loaded.run_id == "ws-root-test"
    assert loaded.graph_id == "g1"
