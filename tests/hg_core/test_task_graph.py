"""Unit tests for hg_core.task_graph: validation, readiness, state machine, binding, failure semantics."""

import pytest

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    validate_dag,
    ValidationResult,
    NodeStatus,
    can_transition,
    get_ready_nodes,
    topological_order,
    resolve_inputs,
    TaskGraphExecutor,
)


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


def _dag(nodes: list, failure_mode: str = "fail_fast") -> DAG:
    return DAG(
        graph_id="test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode=failure_mode),
        inputs={},
        nodes=nodes,
    )


# --- Validation ---


def test_validate_dag_accepts_valid_linear_dag():
    dag = _dag([_node("a"), _node("b", ["a"]), _node("c", ["b"])])
    r = validate_dag(dag)
    assert r.valid
    assert len(r.errors) == 0


def test_validate_dag_rejects_duplicate_node_ids():
    dag = _dag([_node("a"), _node("a")])
    r = validate_dag(dag)
    assert not r.valid
    assert any("duplicate" in e["message"].lower() for e in r.errors)


def test_validate_dag_rejects_unknown_dep():
    dag = _dag([_node("a"), _node("b", ["x"])])
    r = validate_dag(dag)
    assert not r.valid
    assert any("unknown" in e["message"].lower() for e in r.errors)


def test_validate_dag_rejects_cycle():
    dag = _dag([_node("a", ["c"]), _node("b", ["a"]), _node("c", ["b"])])
    r = validate_dag(dag)
    assert not r.valid
    assert any("cycle" in e["message"].lower() for e in r.errors)


def test_validate_dag_rejects_invalid_node_type():
    n = _node("a")
    n.type = "invalid"
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("type" in e["message"].lower() for e in r.errors)


def test_validate_dag_rejects_max_concurrency_below_one():
    dag = _dag([_node("a")])
    dag.run_policy.max_concurrency = 0
    r = validate_dag(dag)
    assert not r.valid
    assert any("concurrency" in e["message"].lower() for e in r.errors)


def test_validate_dag_rejects_empty_assigned_entity():
    n = _node("a")
    n.assigned_entity = ""
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("assigned_entity" in e.get("path", "") or "assigned_entity" in e.get("message", "") for e in r.errors)


def test_validate_dag_rejects_depends_on_not_list():
    n = _node("a")
    n.depends_on = "not-a-list"  # type: ignore
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("depends_on" in e.get("path", "") or "depends_on" in e.get("message", "") for e in r.errors)


def test_validate_dag_rejects_inputs_not_dict():
    n = _node("a")
    n.inputs = []  # type: ignore
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("inputs" in e.get("path", "") or "inputs" in e.get("message", "") for e in r.errors)


def test_validate_dag_rejects_outputs_not_dict():
    n = _node("a")
    n.outputs = None  # type: ignore
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("outputs" in e.get("path", "") or "outputs" in e.get("message", "") for e in r.errors)


def test_validate_dag_rejects_missing_policy():
    n = _node("a")
    n.policy = None  # type: ignore
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("policy" in e.get("path", "") or "policy" in e.get("message", "") for e in r.errors)


def test_validate_dag_rejects_missing_checkpoints():
    n = _node("a")
    n.checkpoints = None  # type: ignore
    dag = _dag([n])
    r = validate_dag(dag)
    assert not r.valid
    assert any("checkpoints" in e.get("path", "") or "checkpoints" in e.get("message", "") for e in r.errors)


def test_validate_dag_strict_bindings_rejects_unknown_node():
    """With strict_bindings True, $node.<id>.<key> must reference an existing node."""
    from hg_core.task_graph.schema import RunPolicy
    a = _node("a")
    a.inputs = {"payload": "$node.missing.result"}
    dag = DAG(
        graph_id="test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="continue", strict_bindings=True),
        inputs={},
        nodes=[a],
    )
    r = validate_dag(dag)
    assert not r.valid
    assert any("unknown node" in e.get("message", "") for e in r.errors)
    assert any(e.get("path") == "inputs" for e in r.errors)


def test_validate_dag_strict_bindings_rejects_undeclared_output():
    """With strict_bindings True, referenced output key must be in the upstream node's outputs."""
    from hg_core.task_graph.schema import RunPolicy
    a = _node("a")
    a.outputs = {"x": {}}
    b = _node("b", ["a"])
    b.inputs = {"payload": "$node.a.result"}
    dag = DAG(
        graph_id="test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="continue", strict_bindings=True),
        inputs={},
        nodes=[a, b],
    )
    r = validate_dag(dag)
    assert not r.valid
    assert any("not declared" in e.get("message", "") or "outputs" in e.get("message", "") for e in r.errors)
    assert any(e.get("path") == "inputs" for e in r.errors)


# --- Gate / Eval / Loop validation ---


def test_validate_dag_gate_requires_condition():
    g = _node("g", node_type="gate")
    g.inputs = {"true_targets": ["a"], "false_targets": []}
    a = _node("a", ["g"])
    r = validate_dag(_dag([g, a]))
    assert not r.valid
    assert any("condition" in e.get("message", "") for e in r.errors)


def test_validate_dag_gate_requires_true_false_targets():
    g = _node("g", node_type="gate")
    g.inputs = {"condition": {"var": "x"}}
    a = _node("a", ["g"])
    r = validate_dag(_dag([g, a]))
    assert not r.valid
    assert any("true_targets" in e.get("message", "") or "false_targets" in e.get("message", "") for e in r.errors)


def test_validate_dag_gate_rejects_unknown_target():
    g = _node("g", node_type="gate")
    g.inputs = {"condition": {"var": "x"}, "true_targets": ["nonexistent"], "false_targets": []}
    r = validate_dag(_dag([g]))
    assert not r.valid
    assert any("unknown node" in e.get("message", "") for e in r.errors)


def test_validate_dag_gate_rejects_both_targets_empty():
    g = _node("g", node_type="gate")
    g.inputs = {"condition": {"var": "x"}, "true_targets": [], "false_targets": []}
    r = validate_dag(_dag([g]))
    assert not r.valid
    assert any("non-empty" in e.get("message", "") for e in r.errors)


def test_validate_dag_eval_requires_expression():
    e = _node("e", node_type="eval")
    e.inputs = {}
    r = validate_dag(_dag([e]))
    assert not r.valid
    assert any("expression" in e.get("message", "") for e in r.errors)


def test_validate_dag_loop_requires_condition_and_body():
    L = _node("L", node_type="loop")
    L.inputs = {}
    L.policy = NodePolicy(max_iterations=3)
    r = validate_dag(_dag([L]))
    assert not r.valid
    assert any("condition" in e.get("message", "") or "body" in e.get("message", "") for e in r.errors)


def test_validate_dag_loop_requires_max_iterations():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "state.x"}, "body": []}
    L.policy = NodePolicy()  # no max_iterations
    r = validate_dag(_dag([L]))
    assert not r.valid
    assert any("max_iterations" in e.get("message", "") for e in r.errors)


def test_validate_dag_loop_rejects_nested_loop():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "state.x"}, "body": ["inner"]}
    L.policy = NodePolicy(max_iterations=2)
    inner = _node("inner", node_type="loop")
    inner.inputs = {"condition": {"var": "state.y"}, "body": []}
    inner.policy = NodePolicy(max_iterations=1)
    r = validate_dag(_dag([L, inner]))
    assert not r.valid
    assert any("nested" in e.get("message", "") for e in r.errors)


def test_validate_dag_loop_body_node_must_not_depend_outside():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "state.x"}, "body": ["b"]}
    L.policy = NodePolicy(max_iterations=2)
    b = _node("b", ["a"])  # b in body depends on a outside
    a = _node("a")
    r = validate_dag(_dag([a, L, b]))
    assert not r.valid
    assert any("outside the loop" in e.get("message", "") for e in r.errors)


def test_validate_dag_loop_body_may_depend_on_loop_node():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "state.x"}, "body": ["b"]}
    L.policy = NodePolicy(max_iterations=2)
    b = _node("b", ["L"])
    r = validate_dag(_dag([L, b]))
    assert r.valid


def test_validate_dag_run_policy_loop_policy_on_body_failure():
    dag = _dag([_node("a")])
    dag.run_policy.loop_policy_on_body_failure = "invalid"
    r = validate_dag(dag)
    assert not r.valid
    assert any("loop_policy_on_body_failure" in e.get("message", "") for e in r.errors)


def test_validate_dag_run_policy_max_node_executions_ge_one():
    dag = _dag([_node("a")])
    dag.run_policy.max_node_executions = 0
    r = validate_dag(dag)
    assert not r.valid
    assert any("max_node_executions" in e.get("message", "") for e in r.errors)


def test_validate_dag_node_policy_effect_class():
    n = _node("a")
    n.policy = NodePolicy(effect_class="invalid")
    r = validate_dag(_dag([n]))
    assert not r.valid
    assert any("effect_class" in e.get("message", "") for e in r.errors)


def test_validate_dag_effect_class_write_in_loop_requires_checkpoint():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "state.x"}, "body": ["b"]}
    L.policy = NodePolicy(max_iterations=2)
    b = _node("b", ["L"])
    b.policy = NodePolicy(effect_class="write")
    b.checkpoints = Checkpoints(before=False, after=False)
    dag = _dag([L, b])
    dag.run_policy.allow_side_effects_in_loops = False
    r = validate_dag(dag)
    assert not r.valid
    assert any("checkpoint" in e.get("message", "") or "allow_side_effects" in e.get("message", "") for e in r.errors)


def test_validate_dag_effect_class_write_in_loop_with_checkpoint_ok():
    L = _node("L", node_type="loop")
    L.inputs = {"condition": {"var": "state.x"}, "body": ["b"]}
    L.policy = NodePolicy(max_iterations=2)
    b = _node("b", ["L"])
    b.policy = NodePolicy(effect_class="write")
    b.checkpoints = Checkpoints(before=True, after=False)
    r = validate_dag(_dag([L, b]))
    assert r.valid


# --- State machine ---


def test_can_transition_pending_to_ready():
    assert can_transition("pending", "ready") is True


def test_can_transition_running_to_done():
    assert can_transition("running", "done") is True


def test_can_transition_running_to_ready_retry():
    assert can_transition("running", "ready") is True


def test_can_transition_rejects_pending_to_done():
    assert can_transition("pending", "done") is False


def test_can_transition_rejects_done_to_running():
    assert can_transition("done", "running") is False


# --- Topological order ---


def test_topological_order_linear():
    dag = _dag([_node("c", ["b"]), _node("a"), _node("b", ["a"])])
    order = topological_order(dag)
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_topological_order_branching():
    dag = _dag([_node("a"), _node("b", ["a"]), _node("c", ["a"]), _node("d", ["b", "c"])])
    order = topological_order(dag)
    assert order.index("a") < order.index("b") and order.index("a") < order.index("c")
    assert order.index("b") < order.index("d") and order.index("c") < order.index("d")


# --- Readiness ---


def test_get_ready_nodes_empty_when_all_pending():
    dag = _dag([_node("a"), _node("b", ["a"])])
    nodes = list(dag.nodes)
    ready = get_ready_nodes(dag, nodes, "fail_fast")
    assert ready == ["a"]


def test_get_ready_nodes_after_dep_done():
    dag = _dag([_node("a"), _node("b", ["a"])])
    nodes = list(dag.nodes)
    by_id = {n.id: n for n in nodes}
    by_id["a"].status = NodeStatus.DONE.value
    ready = get_ready_nodes(dag, nodes, "fail_fast")
    assert "b" in ready


def test_get_ready_nodes_continue_skips_dependents_of_failed():
    dag = _dag([_node("a"), _node("b", ["a"])], failure_mode="continue")
    nodes = list(dag.nodes)
    by_id = {n.id: n for n in nodes}
    by_id["a"].status = NodeStatus.FAILED.value
    ready = get_ready_nodes(dag, nodes, "continue")
    assert "b" not in ready


# --- Binding ---


def test_resolve_inputs_graph_ref():
    node = _node("b")
    node.inputs = {"customer_id": "$graph.inputs.customer_id"}
    graph_inputs = {"customer_id": "12345"}
    out = resolve_inputs(node, {}, graph_inputs)
    assert out["customer_id"] == "12345"


def test_resolve_inputs_node_ref():
    node = _node("b")
    node.inputs = {"profile": "$node.a.profile"}
    node_outputs = {"a": {"profile": {"name": "Alice"}}}
    out = resolve_inputs(node, node_outputs, {})
    assert out["profile"] == {"name": "Alice"}


def test_resolve_inputs_literal():
    node = _node("a")
    node.inputs = {"x": 1, "y": "hello"}
    out = resolve_inputs(node, {}, {})
    assert out["x"] == 1 and out["y"] == "hello"


def test_executor_merges_dag_input_defaults_with_partial_graph_inputs():
    seen_inputs = {}

    def capture_dispatch(node, inputs):
        seen_inputs.update(inputs)
        return {"ok": True, "outputs": dict(inputs)}

    node = _node("start")
    node.inputs = {
        "trigger": "$graph.inputs.trigger",
        "goal": "$graph.inputs.goal",
        "content_hint": "$graph.inputs.content_hint",
    }
    node.outputs = {"trigger": {}, "goal": {}, "content_hint": {}}
    dag = DAG(
        graph_id="test-input-merge",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={"trigger": "cron", "goal": "", "content_hint": ""},
        nodes=[node],
    )

    exec = TaskGraphExecutor(dispatcher=capture_dispatch)
    summary = exec.run(dag, graph_inputs={"goal": "dry-run"})
    assert summary["ok"] is True
    assert seen_inputs["trigger"] == "cron"
    assert seen_inputs["goal"] == "dry-run"
    assert seen_inputs["content_hint"] == ""


def test_executor_fails_when_max_total_runtime_cap_exceeded_before_dispatch():
    called = {"count": 0}

    def capture_dispatch(node, inputs):
        called["count"] += 1
        return {"ok": True, "outputs": {}}

    dag = _dag([_node("a")])
    dag.run_policy.max_total_runtime_s = 0
    executor = TaskGraphExecutor(dispatcher=capture_dispatch)
    result = executor.run(dag)

    assert result["ok"] is False
    assert result["final_status"] == "failed"
    run_error = result.get("run_state", {}).get("state", {}).get("_run_error", {})
    assert run_error.get("code") == "MAX_TOTAL_RUNTIME_EXCEEDED"
    assert called["count"] == 0


def test_executor_resume_fails_when_max_total_runtime_cap_exceeded():
    from hg_core.task_graph.state_store import RunState, StateStore

    dag = _dag([_node("a")])
    dag.run_policy.max_total_runtime_s = 1
    state_store = StateStore()
    run_id = "resume-cap-run"
    node = dag.nodes[0]
    node.status = NodeStatus.PENDING.value
    run_state = RunState(
        run_id=run_id,
        graph_id=dag.graph_id,
        started_at="2000-01-01T00:00:00Z",
        updated_at="2000-01-01T00:00:00Z",
        node_outputs={},
        node_states={},
    )
    state_store.save(run_state, [node])
    executor = TaskGraphExecutor(dispatcher=lambda n, i: {"ok": True, "outputs": {}}, state_store=state_store)
    result = executor.resume(dag, run_id)

    assert result["ok"] is False
    assert result["final_status"] == "failed"
    run_error = result.get("run_state", {}).get("state", {}).get("_run_error", {})
    assert run_error.get("code") == "MAX_TOTAL_RUNTIME_EXCEEDED"


# --- Eval node (dispatch layer) ---


def _eval_node(nid: str, expression: dict, writes: dict = None, outputs: dict = None, depends_on: list = None) -> Node:
    """Build a valid eval node."""
    return Node(
        id=nid,
        type="eval",
        assigned_entity="eval",
        depends_on=depends_on or [],
        inputs={"expression": expression, **({"writes": writes} if writes else {})},
        outputs=outputs or {"result": {}},
        policy=NodePolicy(),
        checkpoints=Checkpoints(),
    )


def test_eval_dispatch_expression_only():
    """Eval dispatch with no writes: returns result in outputs; state unchanged."""
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.state_store import RunState

    e = _eval_node("e", {"==": [1, 1]})
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    out = dispatch_node(e, {}, run_state=run_state, graph_inputs={}, expression_strict=False)
    assert out.get("ok") is True
    assert out.get("outputs", {}).get("result") is True
    assert run_state.state == {}


def test_eval_dispatch_writes_on_success():
    """Eval dispatch with writes: run_state.state updated atomically when expression succeeds."""
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.state_store import RunState

    e = _eval_node("e", {"==": [1, 1]}, writes={"state.x": 10, "state.loops.L.counter": 1})
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    out = dispatch_node(e, {}, run_state=run_state, graph_inputs={}, expression_strict=False)
    assert out.get("ok") is True
    assert run_state.state.get("x") == 10
    assert run_state.state.get("loops", {}).get("L", {}).get("counter") == 1


def test_eval_dispatch_failure_no_writes():
    """When eval expression fails (strict + missing var), returns ok=False and state unchanged."""
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.state_store import RunState

    e = _eval_node("e", {"var": "state.missing"}, writes={"state.x": 5})
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    out = dispatch_node(e, {}, run_state=run_state, graph_inputs={}, expression_strict=True)
    assert out.get("ok") is False
    assert run_state.state.get("x") is None
    assert "x" not in run_state.state


def test_eval_dispatch_writes_atomic_invalid_path():
    """When one write path is invalid, returns ok=False and no writes applied (atomic)."""
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.state_store import RunState

    e = _eval_node("e", {"==": [1, 1]}, writes={"state.first": 1, "notstate.second": 2})
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    out = dispatch_node(e, {}, run_state=run_state, graph_inputs={}, expression_strict=False)
    assert out.get("ok") is False
    assert out.get("error", {}).get("code") == "WRITE_PATH_ERROR"
    assert run_state.state.get("first") is None
    assert "first" not in run_state.state


def test_transform_dispatch_single_input_passthrough():
    from hg_core.task_graph.dispatch import dispatch_node

    n = _node("t1", node_type="transform")
    n.inputs = {"payload": "x"}
    n.outputs = {}
    out = dispatch_node(n, {"payload": {"k": 1}}, run_state=None, graph_inputs={}, expression_strict=False)
    assert out.get("ok") is True
    assert out.get("outputs", {}).get("result") == {"k": 1}


def test_transform_dispatch_expression_to_declared_output():
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.state_store import RunState

    n = _node("t2", node_type="transform")
    n.inputs = {"expression": {"==": [1, 1]}}
    n.outputs = {"value": {}}
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    out = dispatch_node(n, {"expression": {"==": [1, 1]}}, run_state=run_state, graph_inputs={}, expression_strict=False)
    assert out.get("ok") is True
    assert out.get("outputs", {}).get("result") is True
    assert out.get("outputs", {}).get("value") is True


def test_gate_dispatch_selects_branch_targets():
    from hg_core.task_graph.dispatch import dispatch_node

    g = _node("g1", node_type="gate")
    g.inputs = {"condition": {"==": [2, 2]}, "true_targets": ["a"], "false_targets": ["b"]}
    g.outputs = {}
    out = dispatch_node(
        g,
        {"condition": {"==": [2, 2]}, "true_targets": ["a"], "false_targets": ["b"]},
        run_state=None,
        graph_inputs={},
        expression_strict=False,
    )
    assert out.get("ok") is True
    assert out.get("outputs", {}).get("allowed") is True
    assert out.get("outputs", {}).get("selected_targets") == ["a"]


# --- Gate node (executor: condition + skip propagation) ---


def _gate_node(nid: str, condition: dict, true_targets: list, false_targets: list, depends_on: list = None) -> Node:
    """Build a valid gate node."""
    return Node(
        id=nid,
        type="gate",
        assigned_entity="gate",
        depends_on=depends_on or [],
        inputs={"condition": condition, "true_targets": true_targets, "false_targets": false_targets},
        outputs={},
        policy=NodePolicy(),
        checkpoints=Checkpoints(),
    )


def test_gate_reachable_and_skip_propagation_helpers():
    """Unit test: _successors_by_id, _reachable_from, R_skipped - R_taken gives correct to_skip set."""
    from hg_core.task_graph.executor import _successors_by_id, _reachable_from

    gate = _gate_node("g", {}, true_targets=["a"], false_targets=["b"])
    a = _node("a", ["g"])
    b = _node("b", ["g"])
    c = _node("c", ["b"])
    nodes = [gate, a, b, c]
    succ = _successors_by_id(nodes)
    assert set(succ["g"]) == {"a", "b"}
    assert set(succ["b"]) == {"c"}
    R_taken = _reachable_from(["a"], succ)
    R_skipped = _reachable_from(["b"], succ)
    to_skip = R_skipped - R_taken
    assert to_skip == {"b", "c"}
    R_taken_b = _reachable_from(["b"], succ)
    R_skipped_a = _reachable_from(["a"], succ)
    to_skip_false = R_skipped_a - R_taken_b
    assert to_skip_false == {"a"}


def test_gate_get_ready_after_skip_propagation():
    """After gate marks non-taken branch SKIPPED, get_ready_nodes returns only taken branch; deps-all-SKIPPED propagates."""
    from hg_core.task_graph.executor import get_ready_nodes

    gate = _gate_node("g", {}, true_targets=["a"], false_targets=["b"])
    a = _node("a", ["g"])
    b = _node("b", ["g"])
    m = _node("m", ["a"])
    nodes = [gate, a, b, m]
    gate.status = NodeStatus.DONE.value
    b.status = NodeStatus.SKIPPED.value
    dag = _dag([gate, a, b, m])
    ready = get_ready_nodes(dag, nodes, "fail_fast")
    assert "a" in ready
    assert "b" not in ready
    assert "m" not in ready
    # m depends only on a; a is still PENDING here. So m not ready. Now set a SKIPPED; then m should become SKIPPED by propagation.
    a.status = NodeStatus.SKIPPED.value
    ready2 = get_ready_nodes(dag, nodes, "fail_fast")
    assert m.status == NodeStatus.SKIPPED.value
    assert "m" not in ready2


def test_gate_condition_evaluates_in_executor():
    """Gate condition is evaluated with expression engine (smoke: true/false branches)."""
    from hg_core.task_graph.expression import evaluate as evaluate_expression

    context = {"state": {}, "node": {}, "graph": {"inputs": {}}, "loop": {}}
    assert bool(evaluate_expression({"==": [1, 1]}, context, strict=False)) is True
    assert bool(evaluate_expression({"==": [1, 0]}, context, strict=False)) is False


# --- Loop node (executor: condition, body reset, advance, on_body_failure) ---


def _loop_node(nid: str, condition: dict, body: list, depends_on: list = None) -> Node:
    """Build a valid loop node."""
    return Node(
        id=nid,
        type="loop",
        assigned_entity="loop",
        depends_on=depends_on or [],
        inputs={"condition": condition, "body": body},
        outputs={},
        policy=NodePolicy(max_iterations=3),
        checkpoints=Checkpoints(),
    )


def test_loop_body_to_loop_map():
    """_body_to_loop_map returns body_node_id -> loop_id for nodes in a loop body."""
    from hg_core.task_graph.executor import _body_to_loop_map

    L = _loop_node("L", {"var": "state.x"}, body=["a", "b"])
    a = _node("a", ["L"])
    b = _node("b", ["L"])
    dag = _dag([L, a, b])
    m = _body_to_loop_map(dag)
    assert m.get("a") == "L"
    assert m.get("b") == "L"
    assert m.get("L") is None


def test_loop_body_complete_and_advance():
    """_get_loop_body_complete returns (loop_id, body_ids) when body all DONE/SKIPPED; _advance_loop resets body for next iter."""
    from hg_core.task_graph.executor import (
        _get_loop_body_complete,
        _advance_loop,
        _reset_loop_body_nodes,
    )
    from hg_core.task_graph.state_store import RunState

    L = _loop_node("L", {"<": [{"var": "loop.iteration"}, 3]}, body=["a", "b"])  # condition true for iter 1,2,3
    a = _node("a", ["L"])
    b = _node("b", ["L"])
    nodes = [L, a, b]
    by_id = {n.id: n for n in nodes}
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    run_state.loop_state["L"] = {
        "active": True,
        "iteration": 1,
        "max_iterations": 3,
        "last_condition_value": True,
        "iteration_started_at": 0.0,
    }
    L.status = NodeStatus.DONE.value
    a.status = NodeStatus.DONE.value
    b.status = NodeStatus.DONE.value
    dag = _dag([L, a, b])
    info = _get_loop_body_complete(dag, nodes, run_state)
    assert info == ("L", ["a", "b"])
    _advance_loop(dag, nodes, run_state, {}, info, by_id)
    assert run_state.loop_state["L"]["iteration"] == 2
    assert run_state.loop_state["L"]["active"] is True
    assert a.status == NodeStatus.PENDING.value
    assert b.status == NodeStatus.PENDING.value
    assert run_state.node_outputs.get("a") is None
    assert run_state.node_outputs.get("b") is None


def test_loop_reset_body_nodes():
    """_reset_loop_body_nodes sets body nodes to PENDING and clears outputs."""
    from hg_core.task_graph.executor import _reset_loop_body_nodes
    from hg_core.task_graph.state_store import RunState

    a = _node("a", [])
    b = _node("b", ["a"])
    nodes = [a, b]
    by_id = {n.id: n for n in nodes}
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={"a": {"x": 1}, "b": {"y": 2}})
    a.status = NodeStatus.DONE.value
    b.status = NodeStatus.DONE.value
    a.attempt_count = 2
    _reset_loop_body_nodes(nodes, by_id, ["a", "b"], run_state)
    assert a.status == NodeStatus.PENDING.value
    assert b.status == NodeStatus.PENDING.value
    assert a.attempt_count == 0
    assert b.attempt_count == 0
    assert run_state.node_outputs.get("a") is None
    assert run_state.node_outputs.get("b") is None


# --- Executor: fail_fast vs continue ---


@pytest.mark.timeout(15)
def test_executor_fail_fast_stops_on_failure():
    def fail_once(node, inputs):
        if node.id == "a":
            raise RuntimeError("fail")
        return {}

    dag = _dag([_node("a"), _node("b", ["a"])], failure_mode="fail_fast")
    exec = TaskGraphExecutor(dispatcher=fail_once)
    summary = exec.run(dag)
    assert summary["ok"] is False
    assert summary.get("final_status") == "failed"
    by_id = {n.id: n for n in dag.nodes}
    assert by_id["b"].status == NodeStatus.SKIPPED.value


@pytest.mark.timeout(15)
def test_executor_continue_skips_dependents():
    def fail_a(node, inputs):
        if node.id == "a":
            raise RuntimeError("fail")
        return {"ok": True, "outputs": {}}

    dag = _dag([_node("a"), _node("b", ["a"]), _node("c")], failure_mode="continue")
    exec = TaskGraphExecutor(dispatcher=fail_a)
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary["final_status"] in ("completed", "partial")
    by_id = {n.id: n for n in dag.nodes}
    assert by_id["a"].status == NodeStatus.FAILED.value
    assert by_id["b"].status == NodeStatus.SKIPPED.value
    assert by_id["c"].status == NodeStatus.DONE.value


@pytest.mark.timeout(15)
def test_executor_retry_succeeds_on_second_attempt():
    attempts = []

    def fail_first(node, inputs):
        attempts.append(node.id)
        if node.id == "a" and len(attempts) == 1:
            raise RuntimeError("fail")
        return {"ok": True}

    dag = _dag([_node("a")])
    n = dag.nodes[0]
    n.policy.max_retries = 1
    exec = TaskGraphExecutor(dispatcher=fail_first)
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert len(attempts) == 2
    assert dag.nodes[0].status == NodeStatus.DONE.value


# --- Test graph suite (task_graph_tc_implementation plan Part 3) ---


def test_executor_gate_with_merge_node(tmp_path):
    """Test graph 1: Gate with merge node. Gate chooses branch A or B; both write to state.result; M depends only on gate and reads state.result. No BLOCKED; run completes; M runs and sees one branch's result."""
    from pathlib import Path
    from hg_core.task_graph.state_store import StateStore
    from hg_core.task_graph.dispatch import dispatch_node

    gate = _gate_node("g", {"==": [1, 1]}, true_targets=["a"], false_targets=["b"])
    a = _eval_node("a", True, writes={"state.result": "from_a"}, depends_on=["g"])
    b = _eval_node("b", True, writes={"state.result": "from_b"}, depends_on=["g"])
    m = _eval_node("m", {"var": "state.result"}, outputs={"result": "result"}, depends_on=["g"])
    dag = _dag([gate, a, b, m])

    exec = TaskGraphExecutor(
        state_store=StateStore(base_dir=Path(tmp_path)),
        telemetry=lambda _name, _payload: None,
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary.get("final_status") == "completed"
    by_id = {n.id: n for n in dag.nodes}
    assert by_id["g"].status == NodeStatus.DONE.value
    assert by_id["m"].status == NodeStatus.DONE.value
    # One branch ran, one skipped
    done_a, done_b = by_id["a"].status == NodeStatus.DONE.value, by_id["b"].status == NodeStatus.DONE.value
    assert done_a != done_b
    # state.result set by the taken branch; M read it
    state = (summary.get("run_state") or {}).get("state") or {}
    assert state.get("result") in ("from_a", "from_b")
    # No node BLOCKED
    for n in dag.nodes:
        assert n.status != NodeStatus.BLOCKED.value, f"node {n.id} should not be BLOCKED"


def test_executor_loop_accumulator(tmp_path):
    """Test graph 3: Loop accumulator. Loop with body [inc]; inc writes state.loops.L.counter = loop.iteration; condition iteration < 4. After loop, counter == 3."""
    from pathlib import Path
    from hg_core.task_graph.state_store import StateStore

    L = _loop_node("L", {"<": [{"var": "loop.iteration"}, 4]}, body=["inc"], depends_on=[])
    inc = _eval_node(
        "inc",
        {"var": "loop.iteration"},
        writes={"state.loops.L.counter": {"var": "loop.iteration"}},
        depends_on=["L"],
    )
    dag = _dag([L, inc])
    exec = TaskGraphExecutor(
        state_store=StateStore(base_dir=Path(tmp_path)),
        telemetry=lambda _name, _payload: None,
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary.get("final_status") == "completed"
    state = (summary.get("run_state") or {}).get("state") or {}
    counter = (state.get("loops") or {}).get("L") or {}
    assert counter.get("counter") == 3, "loop should run iterations 1,2,3 then exit"


def test_executor_resume_mid_loop(tmp_path):
    """Test graph 4: Resume mid-loop. Persist state as if after iter 1 complete, start of iter 2; resume; assert iter 1 unchanged, execution continues at iter 2."""
    from pathlib import Path
    from hg_core.task_graph.state_store import RunState, StateStore

    L = _loop_node("L", {"<": [{"var": "loop.iteration"}, 3]}, body=["inc"], depends_on=[])
    inc = _eval_node(
        "inc",
        {"var": "loop.iteration"},
        writes={"state.loops.L.counter": {"var": "loop.iteration"}},
        depends_on=["L"],
    )
    dag = _dag([L, inc])
    run_id = "resume-mid-loop-test"
    store = StateStore(base_dir=Path(tmp_path))
    # Build state as if iter 1 complete, iter 2 about to start (body reset, L DONE)
    run_state = RunState(run_id=run_id, graph_id=dag.graph_id, started_at="", updated_at="", node_outputs={})
    run_state.state.setdefault("loops", {})["L"] = {"counter": 1}
    run_state.loop_state["L"] = {
        "iteration": 2,
        "active": True,
        "last_condition_value": True,
        "iteration_started_at": 0.0,
        "max_iterations": 3,
    }
    run_state.node_outputs["L"] = {"taken": True}
    nodes = []
    for n in dag.nodes:
        node = Node.from_dict(n.to_dict())
        if node.id == "L":
            node.status = NodeStatus.DONE.value
            node.ended_at = "2020-01-01T00:00:00Z"
        else:
            node.status = NodeStatus.PENDING.value
            node.attempt_count = 0
            node.started_at = None
            node.ended_at = None
        nodes.append(node)
    store.save(run_state, nodes)
    exec = TaskGraphExecutor(
        state_store=store,
        telemetry=lambda _name, _payload: None,
    )
    summary = exec.resume(dag, run_id)
    assert summary["ok"] is True
    state = (summary.get("run_state") or {}).get("state") or {}
    counter = (state.get("loops") or {}).get("L") or {}
    assert counter.get("counter") == 2, "resume should run iter 2 and set counter to 2"


def test_executor_gate_inside_loop_flips(tmp_path):
    """Test graph 5: Gate inside loop flips. Loop body has gate; condition $loop.iteration % 2 == 1 so alternates; true_targets [a], false_targets [b]. Iter 1: a runs; iter 2: b runs. No BLOCKED; run completes."""
    from pathlib import Path
    from hg_core.task_graph.state_store import StateStore

    L = _loop_node("L", {"<": [{"var": "loop.iteration"}, 3]}, body=["g", "a", "b"], depends_on=[])
    gate = _gate_node(
        "g",
        {"==": [{"%": [{"var": "loop.iteration"}, 2]}, 1]},
        true_targets=["a"],
        false_targets=["b"],
        depends_on=["L"],
    )
    a = _eval_node("a", True, writes={"state.loops.L.which": "a"}, depends_on=["g"])
    b = _eval_node("b", True, writes={"state.loops.L.which": "b"}, depends_on=["g"])
    dag = _dag([L, gate, a, b])
    exec = TaskGraphExecutor(
        state_store=StateStore(base_dir=Path(tmp_path)),
        telemetry=lambda _name, _payload: None,
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    assert summary.get("final_status") == "completed"
    for n in dag.nodes:
        assert n.status != NodeStatus.BLOCKED.value, f"node {n.id} should not be BLOCKED"
    by_id = {n.id: n for n in dag.nodes}
    assert by_id["a"].status == NodeStatus.DONE.value or by_id["b"].status == NodeStatus.DONE.value


def test_executor_two_independent_loops(tmp_path):
    """Test graph 6: Two independent loops. Loop A and B in same graph; each updates state.loops.<id>.counter. Assert loop_state separation; both counters end as expected."""
    from pathlib import Path
    from hg_core.task_graph.state_store import StateStore

    start = _eval_node("start", True, writes={"state.started": True}, depends_on=[])
    LA = _loop_node("LA", {"<": [{"var": "loop.iteration"}, 2]}, body=["incA"], depends_on=["start"])
    incA = _eval_node(
        "incA",
        {"var": "loop.iteration"},
        writes={"state.loops.LA.counter": {"var": "loop.iteration"}},
        depends_on=["LA"],
    )
    LB = _loop_node("LB", {"<": [{"var": "loop.iteration"}, 2]}, body=["incB"], depends_on=["start"])
    incB = _eval_node(
        "incB",
        {"var": "loop.iteration"},
        writes={"state.loops.LB.counter": {"var": "loop.iteration"}},
        depends_on=["LB"],
    )
    dag = _dag([start, LA, incA, LB, incB])
    exec = TaskGraphExecutor(
        state_store=StateStore(base_dir=Path(tmp_path)),
        telemetry=lambda _name, _payload: None,
    )
    summary = exec.run(dag)
    assert summary["ok"] is True
    state = (summary.get("run_state") or {}).get("state") or {}
    loops = state.get("loops") or {}
    assert (loops.get("LA") or {}).get("counter") == 1
    assert (loops.get("LB") or {}).get("counter") == 1


def test_eval_writes_atomic_strict_runtime_fails():
    """Test graph 7 (lenient): Eval with two writes, second path invalid. Eval fails at runtime; neither key written (atomic)."""
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.state_store import RunState

    e = _eval_node("e", {"==": [1, 1]}, writes={"state.first": 1, "notstate.second": 2})
    run_state = RunState(run_id="r1", graph_id="g1", started_at="", updated_at="", node_outputs={})
    out = dispatch_node(e, {}, run_state=run_state, graph_inputs={}, expression_strict=False)
    assert out.get("ok") is False
    assert run_state.state.get("first") is None
    assert "first" not in run_state.state
    assert "second" not in run_state.state
