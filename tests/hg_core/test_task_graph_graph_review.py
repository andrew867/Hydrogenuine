"""Tests for graph_review.review_dag and annotate_in_loop_body (DAG chapter2 Phase 4)."""

import pytest

from hg_core.task_graph.graph_review import (
    ReviewPolicy,
    ReviewIssue,
    annotate_in_loop_body,
    review_dag,
)


def _minimal_dag(nodes: list, run_policy: dict = None) -> dict:
    return {
        "graph_id": "test",
        "version": "1.0",
        "run_policy": run_policy or {"max_concurrency": 1, "failure_mode": "fail_fast"},
        "inputs": {},
        "nodes": nodes,
    }


def test_review_add_write_checkpoint():
    """DAG with write node missing checkpoints.before -> review adds it and reports ADD_WRITE_CHECKPOINT."""
    dag = _minimal_dag([
        {"id": "w", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {"effect_class": "write"}, "checkpoints": {"before": False, "after": False}},
    ])
    reviewed, report = review_dag(dag, ReviewPolicy())
    assert not report["blocked"]
    assert reviewed is not None
    w_node = next(n for n in reviewed["nodes"] if n["id"] == "w")
    assert w_node["checkpoints"].get("before") is True
    codes = [i["code"] for i in report["issues"]]
    assert "ADD_WRITE_CHECKPOINT" in codes


def test_review_write_retry_no_idempotency_blocked():
    """Write node with retries and no idempotency_key -> WRITE_RETRY_NO_IDEMPOTENCY, blocked=True."""
    dag = _minimal_dag([
        {"id": "w", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {"effect_class": "write", "max_retries": 2}, "checkpoints": {"before": True, "after": True}},
    ])
    reviewed, report = review_dag(dag, ReviewPolicy())
    assert report["blocked"] is True
    assert reviewed is None
    codes = [i["code"] for i in report["issues"]]
    assert "WRITE_RETRY_NO_IDEMPOTENCY" in codes


def test_review_clamp_max_iterations():
    """Loop max_iterations above policy cap -> clamped and CLAMP_MAX_ITERATIONS issue."""
    policy = ReviewPolicy(max_iterations_cap=10)
    dag = _minimal_dag([
        {"id": "L", "type": "loop", "assigned_entity": "x", "depends_on": [], "inputs": {"condition": True, "body": []}, "outputs": {}, "policy": {"max_iterations": 100}, "checkpoints": {}},
    ])
    reviewed, report = review_dag(dag, policy)
    assert not report["blocked"]
    assert reviewed is not None
    L_node = next(n for n in reviewed["nodes"] if n["id"] == "L")
    assert L_node["policy"]["max_iterations"] == 10
    codes = [i["code"] for i in report["issues"]]
    assert "CLAMP_MAX_ITERATIONS" in codes


def test_review_write_in_loop_blocked():
    """Write node in loop body with allow_side_effects_in_loops False -> WRITE_IN_LOOP_BLOCKED, blocked."""
    policy = ReviewPolicy(allow_side_effects_in_loops=False)
    dag = _minimal_dag([
        {"id": "L", "type": "loop", "assigned_entity": "x", "depends_on": [], "inputs": {"condition": True, "body": ["w"]}, "outputs": {}, "policy": {"max_iterations": 5}, "checkpoints": {}},
        {"id": "w", "type": "tool", "assigned_entity": "x", "depends_on": ["L"], "inputs": {}, "outputs": {}, "policy": {"effect_class": "write"}, "checkpoints": {"before": True, "after": True}, "_meta": {"in_loop_body": True}},
    ])
    reviewed, report = review_dag(dag, policy)
    assert report["blocked"] is True
    assert reviewed is None
    codes = [i["code"] for i in report["issues"]]
    assert "WRITE_IN_LOOP_BLOCKED" in codes


def test_annotate_in_loop_body():
    """annotate_in_loop_body sets _meta.in_loop_body on body nodes."""
    dag = _minimal_dag([
        {"id": "L", "type": "loop", "assigned_entity": "x", "depends_on": [], "inputs": {"condition": True, "body": ["b1", "b2"]}, "outputs": {}, "policy": {"max_iterations": 3}, "checkpoints": {}},
        {"id": "b1", "type": "tool", "assigned_entity": "x", "depends_on": ["L"], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        {"id": "b2", "type": "tool", "assigned_entity": "x", "depends_on": ["b1"], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
    ])
    annotate_in_loop_body(dag)
    b1 = next(n for n in dag["nodes"] if n["id"] == "b1")
    b2 = next(n for n in dag["nodes"] if n["id"] == "b2")
    assert b1.get("_meta", {}).get("in_loop_body") is True
    assert b2.get("_meta", {}).get("in_loop_body") is True
    L_node = next(n for n in dag["nodes"] if n["id"] == "L")
    assert L_node.get("_meta", {}).get("in_loop_body") is not True  # L is not in its own body


def test_review_force_fail_fast_on_write():
    """When force_fail_fast_on_write and DAG has write node, run_policy.failure_mode becomes fail_fast."""
    dag = _minimal_dag([
        {"id": "w", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {"effect_class": "write"}, "checkpoints": {"before": True, "after": True}},
    ], run_policy={"max_concurrency": 1, "failure_mode": "continue"})
    reviewed, report = review_dag(dag, ReviewPolicy(force_fail_fast_on_write=True))
    assert reviewed is not None
    assert reviewed["run_policy"]["failure_mode"] == "fail_fast"
