"""Unit tests for hg_core.task_graph.expression (safe expression engine for gate/loop/eval)."""

import pytest

from hg_core.task_graph.expression import (
    evaluate,
    resolve_var,
    validate_expression_paths,
)


# --- resolve_var ---


def test_resolve_var_state_dot_path():
    ctx = {"state": {"loops": {"my_loop": {"counter": 5}}}}
    assert resolve_var("state.loops.my_loop.counter", ctx) == 5
    # Missing path: resolve_var returns internal sentinel; evaluate(..., strict=False) yields None
    assert evaluate({"var": "state.loops.my_loop.missing"}, ctx) is None


def test_resolve_var_node():
    ctx = {"node": {"n1": {"out": "hello"}, "n2": {"x": 42}}}
    assert resolve_var("node.n1.out", ctx) == "hello"
    assert resolve_var("node.n2.x", ctx) == 42
    assert evaluate({"var": "node.n3.y"}, ctx) is None


def test_resolve_var_graph_inputs():
    ctx = {"graph": {"inputs": {"topic": "agent memory"}}}
    assert resolve_var("graph.inputs.topic", ctx) == "agent memory"
    assert evaluate({"var": "graph.inputs.missing"}, ctx) is None


def test_resolve_var_loop():
    ctx = {"loop": {"id": "L1", "iteration": 2, "max_iterations": 10, "state": {"c": 3}}}
    assert resolve_var("loop.id", ctx) == "L1"
    assert resolve_var("loop.iteration", ctx) == 2
    assert resolve_var("loop.max_iterations", ctx) == 10
    assert resolve_var("loop.state", ctx) == {"c": 3}


# --- evaluate lenient (default) ---


def test_evaluate_literal():
    assert evaluate(True, {}) is True
    assert evaluate(42, {}) == 42
    assert evaluate("hi", {}) == "hi"
    assert evaluate(None, {}) is None


def test_evaluate_var_missing_lenient():
    assert evaluate({"var": "state.foo"}, {"state": {}}) is None
    assert evaluate({"var": "graph.inputs.x"}, {"graph": {"inputs": {}}}) is None


def test_evaluate_var_present():
    ctx = {"state": {"x": 1}, "graph": {"inputs": {"y": 2}}}
    assert evaluate({"var": "state.x"}, ctx) == 1
    assert evaluate({"var": "graph.inputs.y"}, ctx) == 2


def test_evaluate_not():
    assert evaluate({"!": True}, {}) is False
    assert evaluate({"!": False}, {}) is True
    assert evaluate({"!": None}, {}) is True  # null is false in boolean context


def test_evaluate_and_or():
    assert evaluate({"and": [True, True]}, {}) is True
    assert evaluate({"and": [True, False]}, {}) is False
    assert evaluate({"or": [False, True]}, {}) is True
    # or returns first truthy or last value; missing var → null, so last is None
    assert evaluate({"or": [False, {"var": "state.missing"}]}, {"state": {}}) is None


def test_evaluate_comparison():
    assert evaluate({"==": [1, 1]}, {}) is True
    assert evaluate({"==": [1, 2]}, {}) is False
    assert evaluate({"!=": [1, 2]}, {}) is True
    assert evaluate({"<": [1, 2]}, {}) is True
    assert evaluate({"<=": [2, 2]}, {}) is True
    assert evaluate({">": [3, 2]}, {}) is True
    assert evaluate({">=": [2, 2]}, {}) is True


def test_evaluate_comparison_with_null_lenient():
    # Lenient: comparison with null → false
    assert evaluate({"==": [{"var": "state.missing"}, 1]}, {"state": {}}) is False
    assert evaluate({"<": [1, {"var": "state.missing"}]}, {"state": {}}) is False


def test_evaluate_arithmetic():
    assert evaluate({"+": [1, 2]}, {}) == 3
    assert evaluate({"-": [5, 2]}, {}) == 3
    assert evaluate({"*": [3, 4]}, {}) == 12
    assert evaluate({"%": [7, 3]}, {}) == 1


def test_evaluate_arithmetic_with_null_lenient():
    # Lenient: arithmetic with null → null
    assert evaluate({"+": [1, {"var": "state.missing"}]}, {"state": {}}) is None
    assert evaluate({"-": [{"var": "state.missing"}, 1]}, {"state": {}}) is None


# --- evaluate strict ---


def test_evaluate_strict_missing_var_raises():
    with pytest.raises(ValueError, match="Missing variable path"):
        evaluate({"var": "state.foo"}, {"state": {}}, strict=True)


def test_evaluate_strict_missing_var_with_default():
    assert evaluate({"var": ["state.foo", 99]}, {"state": {}}, strict=True) == 99


def test_evaluate_strict_arithmetic_with_null_raises():
    # Missing var raises in var resolution (before arithmetic)
    with pytest.raises(ValueError, match="Missing variable path"):
        evaluate({"+": [1, {"var": "state.missing"}]}, {"state": {}}, strict=True)


def test_evaluate_strict_arithmetic_explicit_null_raises():
    # Explicit None in arithmetic raises in strict
    with pytest.raises(ValueError, match="null in arithmetic"):
        evaluate({"+": [1, None]}, {}, strict=True)


def test_evaluate_strict_comparison_with_null_raises():
    # In strict mode, missing var raises in var resolution (before comparison)
    with pytest.raises(ValueError, match="Missing variable path"):
        evaluate({"==": [{"var": "state.missing"}, 1]}, {"state": {}}, strict=True)


# --- validate_expression_paths ---


def test_validate_expression_paths_all_present():
    ctx = {"state": {"x": 1}, "graph": {"inputs": {"y": 2}}}
    ok, missing = validate_expression_paths({"var": "state.x"}, ctx)
    assert ok is True
    assert len(missing) == 0


def test_validate_expression_paths_missing():
    ctx = {"state": {}}
    ok, missing = validate_expression_paths({"var": "state.foo"}, ctx)
    assert ok is False
    assert "state.foo" in missing


def test_validate_expression_paths_nested():
    ctx = {"state": {"a": 1}, "graph": {"inputs": {}}}
    expr = {"and": [{"var": "state.a"}, {"==": [{"var": "graph.inputs.b"}, 0]}]}
    ok, missing = validate_expression_paths(expr, ctx)
    assert ok is False
    assert "graph.inputs.b" in missing
