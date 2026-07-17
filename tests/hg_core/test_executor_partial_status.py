"""Executor final_status when the graph exits with incomplete nodes."""

from hg_core.task_graph.executor import compute_final_run_status
from hg_core.task_graph.schema import Checkpoints, Node, NodePolicy
from hg_core.task_graph.state_machine import NodeStatus


def _node(node_id: str, status: str | None) -> Node:
    return Node(
        id=node_id,
        type="tool",
        assigned_entity="test",
        depends_on=[],
        inputs={},
        outputs={},
        checkpoints=Checkpoints(before=False, after=False),
        policy=NodePolicy.from_dict({"timeout_s": 30, "max_retries": 0}),
        status=status,
    )


def test_compute_final_run_status_partial_when_pending_nodes_remain():
    nodes = [
        _node("a", NodeStatus.DONE.value),
        _node("b", NodeStatus.PENDING.value),
    ]
    assert compute_final_run_status(nodes, "fail_fast") == "partial"


def test_compute_final_run_status_completed_when_all_terminal():
    nodes = [
        _node("a", NodeStatus.DONE.value),
        _node("b", NodeStatus.SKIPPED.value),
    ]
    assert compute_final_run_status(nodes, "fail_fast") == "completed"


def test_compute_final_run_status_failed_on_fail_fast_with_failure():
    nodes = [
        _node("a", NodeStatus.DONE.value),
        _node("b", NodeStatus.FAILED.value),
    ]
    assert compute_final_run_status(nodes, "fail_fast") == "failed"
