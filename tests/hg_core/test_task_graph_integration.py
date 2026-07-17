"""Integration tests for hg_core.task_graph: linear DAG, branching, retry, skip, checkpoint, resume."""

import pytest
from pathlib import Path

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    load_dag,
    save_dag,
    TaskGraphExecutor,
    validate_dag,
)
from hg_core.task_graph.state_store import StateStore, RunState


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


def test_linear_dag_a_b_c(tmp_path):
    """Linear DAG A -> B -> C runs in order with stub dispatch."""
    dag = DAG(
        graph_id="linear",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"]), _node("c", ["b"])],
    )
    order = []
    def record_order(node, inputs):
        order.append(node.id)
        return {"ok": True, "outputs": {"ran": node.id}}
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(dispatcher=record_order, state_store=store)
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["final_status"] == "completed"
    assert order == ["a", "b", "c"]
    assert summary["nodes"]["a"]["status"] == "done"
    assert summary["nodes"]["b"]["status"] == "done"
    assert summary["nodes"]["c"]["status"] == "done"


def test_branching_dag_a_to_bc_to_d(tmp_path):
    """Branching A -> B, A -> C -> D: B and C run after A, D after B and C."""
    dag = DAG(
        graph_id="branch",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=2, failure_mode="fail_fast"),
        inputs={},
        nodes=[
            _node("a"),
            _node("b", ["a"]),
            _node("c", ["a"]),
            _node("d", ["b", "c"]),
        ],
    )
    order = []
    def record(node, inputs):
        order.append(node.id)
        return {"ok": True, "outputs": {}}
    exec = TaskGraphExecutor(dispatcher=record, state_store=StateStore(base_dir=tmp_path / "runs"))
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert "a" in order
    assert order.index("a") < order.index("b") and order.index("a") < order.index("c")
    assert order.index("b") < order.index("d") and order.index("c") < order.index("d")
    assert summary["nodes"]["d"]["status"] == "done"


def test_upstream_failure_causes_downstream_skip(tmp_path):
    """Under continue mode, when A fails, B (depends on A) is skipped."""
    def fail_a(node, inputs):
        if node.id == "a":
            raise RuntimeError("fail")
        return {"ok": True, "outputs": {}}
    dag = DAG(
        graph_id="skip",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="continue"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"])],
    )
    exec = TaskGraphExecutor(dispatcher=fail_a, state_store=StateStore(base_dir=tmp_path / "runs"))
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["nodes"]["a"]["status"] == "failed"
    assert summary["nodes"]["b"]["status"] == "skipped"


def test_checkpoint_hook_invoked(tmp_path):
    """When checkpoints.before/after are set, overseer is called."""
    calls = []
    class MockOverseer:
        def checkpoint_before(self, node, run_state):
            calls.append(("before", node.id))
        def checkpoint_after(self, node, run_state):
            calls.append(("after", node.id))
    a = _node("a")
    a.checkpoints.before = True
    a.checkpoints.after = True
    dag = DAG(
        graph_id="check",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[a],
    )
    exec = TaskGraphExecutor(
        state_store=StateStore(base_dir=tmp_path / "runs"),
        overseer=MockOverseer(),
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert ("before", "a") in calls
    assert ("after", "a") in calls


def test_persisted_state_reload(tmp_path):
    """Run a DAG, then load persisted state by run_id."""
    dag = DAG(
        graph_id="persist",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a")],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(state_store=store)
    summary = exec.run(dag)
    run_id = summary["run_id"]
    resumed = exec.resume(dag, run_id)
    assert resumed["ok"] is True
    assert resumed["run_id"] == run_id
    assert resumed["graph_id"] == "persist"
    assert resumed["final_status"] == "completed"


def test_retry_success_on_second_attempt(tmp_path):
    """Node that fails once then succeeds on retry."""
    attempts = []
    def fail_first(node, inputs):
        attempts.append(node.id)
        if len(attempts) == 1:
            raise RuntimeError("first")
        return {"ok": True, "outputs": {}}
    a = _node("a")
    a.policy.max_retries = 1
    dag = DAG(
        graph_id="retry",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[a],
    )
    exec = TaskGraphExecutor(dispatcher=fail_first, state_store=StateStore(base_dir=tmp_path / "runs"))
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert len(attempts) == 2
    assert summary["nodes"]["a"]["status"] == "done"
