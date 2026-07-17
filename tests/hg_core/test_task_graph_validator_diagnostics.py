"""Tests for validate_dag_with_diagnostics and Diagnostic codes (DAG chapter2 Phase 0)."""

import pytest

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
)
from hg_core.task_graph.validator_diagnostics import (
    Diagnostic,
    validate_dag_with_diagnostics,
)


def _node(nid: str, depends_on: list = None, node_type: str = "tool", **kwargs) -> Node:
    policy = kwargs.pop("policy", NodePolicy())
    checkpoints = kwargs.pop("checkpoints", Checkpoints())
    return Node(
        id=nid,
        type=node_type,
        assigned_entity=kwargs.get("assigned_entity", "stub"),
        depends_on=depends_on or [],
        inputs=kwargs.get("inputs", {}),
        outputs=kwargs.get("outputs", {}),
        policy=policy,
        checkpoints=checkpoints,
    )


def _dag(nodes: list, **run_policy_kw) -> DAG:
    return DAG(
        graph_id="test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast", **run_policy_kw),
        inputs={},
        nodes=nodes,
    )


# --- Return shape ---


def test_validate_dag_with_diagnostics_return_shape_valid():
    dag = _dag([_node("a"), _node("b", ["a"])])
    out = validate_dag_with_diagnostics(dag)
    assert "ok" in out
    assert "errors" in out
    assert "warnings" in out
    assert isinstance(out["ok"], bool)
    assert isinstance(out["errors"], list)
    assert isinstance(out["warnings"], list)
    assert out["ok"] is True
    assert len(out["errors"]) == 0


def test_validate_dag_with_diagnostics_return_shape_invalid():
    dag = _dag([_node("a"), _node("a")])
    out = validate_dag_with_diagnostics(dag)
    assert out["ok"] is False
    assert len(out["errors"]) >= 1
    for e in out["errors"]:
        assert isinstance(e, Diagnostic)
        assert e.level == "error"
        assert e.code
        assert e.message


def test_validate_dag_with_diagnostics_accepts_dict():
    dag_dict = _dag([_node("a")]).to_dict()
    out = validate_dag_with_diagnostics(dag_dict)
    assert out["ok"] is True
    assert out["errors"] == []


# --- Diagnostic codes (one test per code) ---


def test_diagnostic_code_duplicate_node_id():
    dag = _dag([_node("a"), _node("a")])
    out = validate_dag_with_diagnostics(dag)
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "DUPLICATE_NODE_ID" in codes


def test_diagnostic_code_unknown_dependency():
    dag = _dag([_node("a"), _node("b", ["x"])])
    out = validate_dag_with_diagnostics(dag)
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "UNKNOWN_DEPENDENCY" in codes


def test_diagnostic_code_cycle_detected():
    dag = _dag([_node("a", ["c"]), _node("b", ["a"]), _node("c", ["b"])])
    out = validate_dag_with_diagnostics(dag)
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "CYCLE_DETECTED" in codes


def test_diagnostic_code_invalid_node_type():
    n = _node("a")
    n.type = "invalid"
    out = validate_dag_with_diagnostics(_dag([n]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "INVALID_NODE_TYPE" in codes


def test_diagnostic_code_invalid_gate_target():
    g = _node("g", node_type="gate")
    g.inputs = {"condition": {"var": "x"}, "true_targets": ["nonexistent"], "false_targets": []}
    out = validate_dag_with_diagnostics(_dag([g]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "INVALID_GATE_TARGET" in codes


def test_diagnostic_code_invalid_loop_body():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "x"}, "body": ["missing"]}
    L.policy = NodePolicy(max_iterations=2)
    out = validate_dag_with_diagnostics(_dag([L]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "INVALID_LOOP_BODY" in codes


def test_diagnostic_code_loop_body_depends_outside():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "x"}, "body": ["b"]}
    L.policy = NodePolicy(max_iterations=2)
    a = _node("a")
    b = _node("b", ["a"])
    out = validate_dag_with_diagnostics(_dag([a, L, b]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "INVALID_LOOP_BODY" in codes


def test_diagnostic_code_nested_loop_disallowed():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "x"}, "body": ["inner"]}
    L.policy = NodePolicy(max_iterations=2)
    inner = _node("inner", node_type="loop")
    inner.inputs = {"condition": {"var": "y"}, "body": []}
    inner.policy = NodePolicy(max_iterations=1)
    out = validate_dag_with_diagnostics(_dag([L, inner]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "NESTED_LOOP_DISALLOWED" in codes


def test_diagnostic_code_write_in_loop_blocked():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "x"}, "body": ["b"]}
    L.policy = NodePolicy(max_iterations=2)
    b = _node("b", ["L"])
    b.policy = NodePolicy(effect_class="write")
    b.checkpoints = Checkpoints(before=False, after=False)
    dag = _dag([L, b])
    dag.run_policy.allow_side_effects_in_loops = False
    out = validate_dag_with_diagnostics(dag)
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "WRITE_IN_LOOP_BLOCKED" in codes


def test_diagnostic_code_write_retry_no_idempotency():
    n = _node("w")
    n.policy = NodePolicy(effect_class="write", max_retries=2, idempotency_key=None)
    out = validate_dag_with_diagnostics(_dag([n]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "WRITE_RETRY_NO_IDEMPOTENCY" in codes


def test_diagnostic_code_write_retry_with_idempotency_ok():
    n = _node("w")
    n.policy = NodePolicy(effect_class="write", max_retries=2, idempotency_key="key:1")
    out = validate_dag_with_diagnostics(_dag([n]))
    assert out["ok"], [e.code for e in out["errors"]]


def test_diagnostic_code_missing_graph_id():
    dag = _dag([_node("a")])
    dag.graph_id = ""
    out = validate_dag_with_diagnostics(dag)
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "MISSING_GRAPH_ID" in codes


def test_diagnostic_code_invalid_run_policy():
    dag = _dag([_node("a")])
    dag.run_policy.max_concurrency = 0
    out = validate_dag_with_diagnostics(dag)
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "INVALID_RUN_POLICY" in codes or "INVALID_POLICY_VALUE" in codes


def test_diagnostic_code_missing_field_assigned_entity():
    n = _node("a")
    n.assigned_entity = ""
    out = validate_dag_with_diagnostics(_dag([n]))
    assert not out["ok"]
    codes = [e.code for e in out["errors"]]
    assert "MISSING_FIELD" in codes or any("assigned_entity" in (e.field_path or e.message or "") for e in out["errors"])
