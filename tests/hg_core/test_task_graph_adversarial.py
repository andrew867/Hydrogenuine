"""Adversarial tests for hg_core.task_graph: malformed DAGs, duplicates, cycles, missing outputs."""

import json
import pytest
from pathlib import Path

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    load_dag,
    validate_dag,
    TaskGraphExecutor,
)
from hg_core.task_graph.state_store import StateStore


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


def test_malformed_dag_json_rejected(tmp_path):
    """Invalid JSON or missing required fields should be caught on load or validate."""
    bad = tmp_path / "bad.json"
    bad.write_text("{ invalid json")
    with pytest.raises(Exception):
        load_dag(bad)

    bad2 = tmp_path / "bad2.json"
    bad2.write_text('{"graph_id": "x", "nodes": [{"id": "a"}]}')  # missing required node fields
    with pytest.raises(Exception):
        load_dag(bad2)


def test_validate_rejects_duplicate_ids():
    dag = DAG(
        graph_id="dup",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a"), _node("a")],
    )
    r = validate_dag(dag)
    assert not r.valid
    assert any("duplicate" in e["message"].lower() for e in r.errors)


def test_validate_rejects_cycle():
    dag = DAG(
        graph_id="cycle",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[_node("a", ["c"]), _node("b", ["a"]), _node("c", ["b"])],
    )
    r = validate_dag(dag)
    assert not r.valid
    assert any("cycle" in e["message"].lower() for e in r.errors)


def test_executor_handles_missing_upstream_output_gracefully(tmp_path):
    """When a node references $node.other.x but other produced no output, resolve_inputs returns the ref string; dispatcher can still run (stub)."""
    a = _node("a")
    a.outputs = {"out": "x"}
    b = _node("b", ["a"])
    b.inputs = {"ref": "$node.a.out"}
    dag = DAG(
        graph_id="ref",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=[a, b],
    )
    # Stub dispatcher returns {} so a produces nothing; b's input ref stays unresolved
    exec = TaskGraphExecutor(state_store=StateStore(base_dir=tmp_path / "runs"))
    summary = exec.run(dag)
    # Executor still runs; b gets inputs with ref possibly still "$node.a.out" or missing
    assert "run_id" in summary
    assert summary["nodes"]["a"]["status"] == "done"
    # b may run with unresolved ref (implementation-dependent)
    assert summary["nodes"]["b"]["status"] in ("done", "blocked", "failed")
