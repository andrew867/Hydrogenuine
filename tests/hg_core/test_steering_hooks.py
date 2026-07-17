"""Tests for Steering Chapter 1: before_node / after_node hook contract."""

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


def test_before_and_after_called_for_each_node(tmp_path):
    """Executor invokes before_node and after_node for each dispatched node in order."""
    before_calls = []
    after_calls = []

    class TestOverseer:
        def before_node(self, node, run_state):
            before_calls.append(node.id)

        def after_node(self, node, run_state, result):
            after_calls.append((node.id, result.get("ok") if isinstance(result, dict) else None))

    dag = DAG(
        graph_id="steering_linear",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"]), _node("c", ["b"])],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(
        state_store=store,
        overseer=TestOverseer(),
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["final_status"] == "completed"
    assert before_calls == ["a", "b", "c"]
    assert len(after_calls) == 3
    assert [nid for nid, _ in after_calls] == ["a", "b", "c"]
    assert all(ok is True for _, ok in after_calls)


def test_payloads_contain_node_id_run_id_graph_id(tmp_path):
    """before_node and after_node receive node with .id and run_state with .run_id, .graph_id."""
    seen_before = []
    seen_after = []

    class TestOverseer:
        def before_node(self, node, run_state):
            seen_before.append({
                "node_id": getattr(node, "id", None),
                "run_id": getattr(run_state, "run_id", None),
                "graph_id": getattr(run_state, "graph_id", None),
            })

        def after_node(self, node, run_state, result):
            seen_after.append({
                "node_id": getattr(node, "id", None),
                "run_id": getattr(run_state, "run_id", None),
                "graph_id": getattr(run_state, "graph_id", None),
            })

    dag = DAG(
        graph_id="payload_check",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a")],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(state_store=store, overseer=TestOverseer())
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert len(seen_before) == 1 and len(seen_after) == 1
    assert seen_before[0]["node_id"] == "a"
    assert seen_before[0]["graph_id"] == "payload_check"
    assert seen_before[0]["run_id"] is not None
    assert seen_after[0]["node_id"] == "a"
    assert seen_after[0]["graph_id"] == "payload_check"
    assert seen_after[0]["run_id"] == seen_before[0]["run_id"]


def test_no_overseer_runs_without_error(tmp_path):
    """Executor with overseer=None runs DAG successfully."""
    dag = DAG(
        graph_id="no_overseer",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"])],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(state_store=store, overseer=None)
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["final_status"] == "completed"


def test_overseer_without_hooks_runs_without_error(tmp_path):
    """Overseer with only checkpoint_before/checkpoint_after (no before_node/after_node) runs successfully."""
    class CheckpointOnlyOverseer:
        def checkpoint_before(self, node, run_state):
            pass

        def checkpoint_after(self, node, run_state):
            pass

    dag = DAG(
        graph_id="checkpoint_only",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a")],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(state_store=store, overseer=CheckpointOnlyOverseer())
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["final_status"] == "completed"


def test_before_node_block_skips_dispatch_and_calls_after_node(tmp_path):
    """When before_node returns {"block": True, "reason": "policy"}, node is not dispatched and gets STEERING_BLOCKED."""
    dispatched = []
    after_results = []

    class BlockingOverseer:
        def before_node(self, node, run_state):
            if node.id == "b":
                return {"block": True, "reason": "policy"}
            return None

        def after_node(self, node, run_state, result):
            after_results.append((node.id, result))

    def record_dispatch(node, inputs):
        dispatched.append(node.id)
        return {"ok": True, "outputs": {}}

    dag = DAG(
        graph_id="block_b",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="continue"),
        inputs={},
        nodes=[_node("a"), _node("b", ["a"]), _node("c", ["b"])],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(
        state_store=store,
        overseer=BlockingOverseer(),
        dispatcher=record_dispatch,
    )
    summary = exec.run(dag)
    # a runs, b is blocked by steering, c is skipped (depends on b)
    assert "a" in dispatched
    assert "b" not in dispatched
    assert summary["nodes"]["a"]["status"] == "done"
    assert summary["nodes"]["b"]["status"] == "blocked"
    assert summary["nodes"]["b"].get("error", {}).get("code") == "STEERING_BLOCKED"
    # after_node was called for a (ok) and for b (blocked result)
    assert len(after_results) == 2
    assert after_results[0][0] == "a" and after_results[0][1].get("ok") is True
    assert after_results[1][0] == "b" and after_results[1][1].get("ok") is False
    assert after_results[1][1].get("error", {}).get("code") == "STEERING_BLOCKED"


def test_dag_checkpoint_adapter_steering_and_checkpoint_hooks(tmp_path):
    """DAGCheckpointAdapter has before_node/after_node; when node has checkpoints, checkpoint_before/after also run."""
    try:
        from hg_overseer.overseer_core.dag_hooks import DAGCheckpointAdapter
    except ImportError:
        pytest.skip("hg_overseer not installed")

    calls = []

    class RecordingAdapter(DAGCheckpointAdapter):
        def before_node(self, node, run_state):
            calls.append(("before_node", node.id))
            return super().before_node(node, run_state)

        def after_node(self, node, run_state, result):
            calls.append(("after_node", node.id))
            super().after_node(node, run_state, result)

        def checkpoint_before(self, node, run_state):
            calls.append(("checkpoint_before", node.id))
            super().checkpoint_before(node, run_state)

        def checkpoint_after(self, node, run_state):
            calls.append(("checkpoint_after", node.id))
            super().checkpoint_after(node, run_state)

    a = _node("a")
    a.checkpoints.before = True
    a.checkpoints.after = True
    dag = DAG(
        graph_id="adapter_check",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[a],
    )
    store = StateStore(base_dir=tmp_path / "runs")
    exec = TaskGraphExecutor(
        state_store=store,
        overseer=RecordingAdapter(),
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["final_status"] == "completed"
    assert ("before_node", "a") in calls
    assert ("after_node", "a") in calls
    assert ("checkpoint_before", "a") in calls
    assert ("checkpoint_after", "a") in calls
    # Order: before_node -> checkpoint_before -> ... -> checkpoint_after -> after_node
    assert calls.index(("before_node", "a")) < calls.index(("checkpoint_before", "a"))
    assert calls.index(("checkpoint_after", "a")) < calls.index(("after_node", "a"))
