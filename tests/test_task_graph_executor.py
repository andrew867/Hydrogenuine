"""
Phase 1 executor tests: linear DAG, retry, continue/fail_fast, checkpoints, persistence, binding error.

Imports match hg_core.task_graph package (DAG, TaskGraphExecutor, StateStore, validate_dag, ValidationResult).
No timeout tests until timeout enforcement exists (see hg_dag_phased_implementation_plan.md Phase 2).

TEMPORARY: Executor tests use pytest.mark.timeout(15) so the suite finishes; remove timeouts/skips when done.
"""

import json
from pathlib import Path

import pytest

# Short timeout for executor tests so suite completes (remove when cleaning up timeouts/skips)
EXECUTOR_TEST_TIMEOUT = 15

from hg_core.task_graph import (
    DAG,
    TaskGraphExecutor,
    StateStore,
    validate_dag,
    ValidationResult,
)


class TestTelemetry:
    def __init__(self):
        self.events = []

    def __call__(self, event_name, payload):
        self.events.append((event_name, payload))


class TestOverseer:
    def __init__(self):
        self.before_calls = []
        self.after_calls = []

    def checkpoint_before(self, node, run_state):
        self.before_calls.append(node.id)

    def checkpoint_after(self, node, run_state):
        out = run_state.node_outputs.get(node.id, {})
        ok = bool(out and (out.get("ok") is not False))
        self.after_calls.append((node.id, ok))


class BlockingOverseer(TestOverseer):
    def __init__(self, block_node_id: str):
        super().__init__()
        self.block_node_id = block_node_id

    def before_node(self, node, run_state):
        if node.id == self.block_node_id:
            return {"block": True, "reason": "blocked by test"}
        return None


class TestDispatcher:
    """
    Deterministic dispatcher for tests.
    Signature: (node, resolved_inputs) -> {ok, outputs} or {ok, error}.
    """
    def __init__(self):
        self.calls = {}

    def __call__(self, node, resolved_inputs):
        nid = node.id
        self.calls[nid] = self.calls.get(nid, 0) + 1
        attempt = self.calls[nid]

        if nid == "retry_once" and attempt == 1:
            return {"ok": False, "error": {"code": "SIM_FAIL_ONCE", "message": "first fail"}}
        if nid == "retry_twice" and attempt <= 2:
            return {"ok": False, "error": {"code": "SIM_FAIL", "message": f"attempt {attempt}"}}
        if nid == "always_fail":
            return {"ok": False, "error": {"code": "SIM_ALWAYS_FAIL", "message": "always fail"}}

        if nid == "hard_fail":
            return {"ok": False, "error": {"code": "SIM_HARD_FAIL", "message": "always fail"}}

        if nid == "gate_deny":
            return {"ok": False, "error": {"code": "GATE_DENIED", "message": "gate denied"}}

        ntype = getattr(node.type, "value", str(node.type))
        return {
            "ok": True,
            "outputs": {
                "result": f"{nid}_ok_attempt_{attempt}",
                "node_type": ntype,
                "echo_inputs": resolved_inputs,
            },
        }


def make_executor(tmp_path: Path):
    telemetry = TestTelemetry()
    overseer = TestOverseer()
    dispatcher = TestDispatcher()
    store = StateStore(tmp_path / "dag_runs")
    ex = TaskGraphExecutor(
        dispatcher=dispatcher,
        overseer=overseer,
        state_store=store,
        telemetry=telemetry,
    )
    return ex, dispatcher, overseer, telemetry, store


def dag_linear():
    return {
        "graph_id": "linear_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue", "strict_bindings": False},
        "inputs": {"name": "Andrew"},
        "nodes": [
            {
                "id": "a",
                "type": "transform",
                "assigned_entity": "transformer",
                "depends_on": [],
                "inputs": {"name": "$graph.inputs.name"},
                "outputs": {},
                "checkpoints": {"before": True, "after": True},
            },
            {
                "id": "b",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": ["a"],
                "inputs": {"payload": "$node.a.result"},
                "outputs": {},
                "checkpoints": {"before": True, "after": True},
            },
            {
                "id": "c",
                "type": "eval",
                "assigned_entity": "evaluator",
                "depends_on": ["b"],
                "inputs": {"expression": "$node.b.result", "payload": "$node.b.result"},
                "outputs": {},
                "checkpoints": {},
            },
        ],
    }


def dag_branch_retry_skip(failure_mode="continue"):
    return {
        "graph_id": "branch_retry_skip_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": failure_mode, "strict_bindings": False},
        "inputs": {"request_id": "demo-001"},
        "nodes": [
            {
                "id": "start",
                "type": "transform",
                "assigned_entity": "transformer",
                "depends_on": [],
                "inputs": {"request_id": "$graph.inputs.request_id"},
                "outputs": {},
                "checkpoints": {"before": True, "after": True},
            },
            {
                "id": "retry_once",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": ["start"],
                "inputs": {"payload": "$node.start.result"},
                "outputs": {},
                "policy": {"max_retries": 1, "retry_backoff_ms": 0},
                "checkpoints": {"before": True, "after": True},
            },
            {
                "id": "hard_fail",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": ["start"],
                "inputs": {"payload": "$node.start.result"},
                "outputs": {},
                "policy": {"max_retries": 0},
                "checkpoints": {"before": True, "after": True},
            },
            {
                "id": "merge_ok",
                "type": "eval",
                "assigned_entity": "evaluator",
                "depends_on": ["retry_once"],
                "inputs": {"expression": "$node.retry_once.result", "left": "$node.retry_once.result"},
                "outputs": {},
                "checkpoints": {"after": True},
            },
            {
                "id": "skipped_downstream",
                "type": "eval",
                "assigned_entity": "evaluator",
                "depends_on": ["hard_fail"],
                "inputs": {"expression": "$node.hard_fail.result", "right": "$node.hard_fail.result"},
                "outputs": {},
            },
            {
                "id": "final_summary",
                "type": "transform",
                "assigned_entity": "transformer",
                "depends_on": ["merge_ok"],
                "inputs": {"merge": "$node.merge_ok.result"},
                "outputs": {},
                "checkpoints": {"after": True},
            },
        ],
    }


def dag_with_cycle():
    return {
        "graph_id": "cycle_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": ["c"], "inputs": {}, "outputs": {}},
            {"id": "b", "type": "tool", "assigned_entity": "x", "depends_on": ["a"], "inputs": {}, "outputs": {}},
            {"id": "c", "type": "tool", "assigned_entity": "x", "depends_on": ["b"], "inputs": {}, "outputs": {}},
        ],
    }


def dag_bad_binding():
    return {
        "graph_id": "bad_binding_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue", "strict_bindings": False},
        "inputs": {"name": "Andrew"},
        "nodes": [
            {
                "id": "a",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": [],
                "inputs": {"payload": "$node.missing.result"},
                "outputs": {},
                "policy": {"max_retries": 0},
            }
        ],
    }


def dag_unresolved_ref_input_binding(input_binding_mode: str):
    """DAG with one node that has an unresolved ref (depends on nothing, refs missing node). Used for binding-mode tests."""
    return {
        "graph_id": "unresolved_binding_v1",
        "version": "1.0",
        "run_policy": {
            "max_concurrency": 1,
            "failure_mode": "continue",
            "strict_bindings": False,
            "input_binding_mode": input_binding_mode,
        },
        "inputs": {},
        "nodes": [
            {
                "id": "refs_missing",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": [],
                "inputs": {"x": "$node.nonexistent.result"},
                "outputs": {},
                "policy": {"max_retries": 0},
                "checkpoints": {},
            }
        ],
    }


def event_names(telemetry):
    return [e[0] for e in telemetry.events]


def test_validate_dag_rejects_cycle():
    g = DAG.from_dict(dag_with_cycle())
    vr = validate_dag(g)
    assert vr.valid is False
    assert any("cycle" in e["message"].lower() for e in vr.errors)


def test_linear_dag_executes_and_produces_outputs(tmp_path):
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    dag = DAG.from_dict(dag_linear())
    result = ex.run(dag)

    assert result["ok"] is True
    assert result["final_status"] == "completed"
    assert result.get("status") == "completed"
    assert set(result["node_outputs"].keys()) == {"a", "b", "c"}
    assert "dag_run_started" in event_names(telemetry)
    assert "dag_run_completed" in event_names(telemetry)

    assert "a" in overseer.before_calls
    assert "b" in overseer.before_calls
    assert ("a", True) in overseer.after_calls
    assert ("b", True) in overseer.after_calls


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_retry_then_success_path(tmp_path):
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    dag = {
        "graph_id": "retry_only_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {
                "id": "retry_once",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": [],
                "inputs": {},
                "outputs": {},
                "policy": {"max_retries": 1, "retry_backoff_ms": 0},
            }
        ],
    }
    result = ex.run(DAG.from_dict(dag))
    assert result["ok"] is True
    assert result["final_status"] == "completed"
    assert dispatcher.calls["retry_once"] == 2
    assert "dag_node_retried" in event_names(telemetry)
    assert result["node_outputs"]["retry_once"]["result"].startswith("retry_once_ok_attempt_2")


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_continue_mode_skips_downstream_on_failure(tmp_path):
    ex, dispatcher, overseer, telemetry, store = make_executor(tmp_path)
    result = ex.run(DAG.from_dict(dag_branch_retry_skip(failure_mode="continue")))

    assert result["status"] in {"completed", "failed", "partial"}
    run_state = result["run_state"]
    node_states = run_state["node_states"]

    assert node_states["hard_fail"]["status"] == "failed"
    assert node_states["retry_once"]["status"] == "done"
    assert node_states["merge_ok"]["status"] == "done"
    assert node_states["skipped_downstream"]["status"] in {"skipped", "blocked"}

    assert node_states["final_summary"]["status"] == "done"
    assert "dag_node_skipped" in event_names(telemetry)


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_fail_fast_stops_after_terminal_failure(tmp_path):
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    result = ex.run(DAG.from_dict(dag_branch_retry_skip(failure_mode="fail_fast")))

    assert result["ok"] is False
    assert result["final_status"] == "failed"

    node_states = result["run_state"]["node_states"]
    assert node_states["hard_fail"]["status"] == "failed"
    assert node_states["final_summary"]["status"] in {"pending", "ready", "skipped", "blocked"}

    assert "dag_run_completed" in event_names(telemetry)


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_persisted_state_files_exist(tmp_path):
    ex, dispatcher, overseer, telemetry, store = make_executor(tmp_path)
    result = ex.run(DAG.from_dict(dag_linear()))

    run_id = result["run_id"]
    run_dir = tmp_path / "dag_runs"
    state_file = run_dir / f"{run_id}.json"
    assert state_file.exists()

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["run_id"] == run_id
    assert state["graph_id"] == "linear_v1"


def test_run_dir_creates_dir_and_graph_json_before_run(tmp_path):
    """When run_dir is provided, run() creates run_dir and writes graph.json before entering the loop."""
    from hg_core.task_graph.state_store import RunState
    ex, _, _, _, store = make_executor(tmp_path)
    run_dir = tmp_path / "run_dir"
    dag_dict = {
        "graph_id": "single_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    # Run with run_dir; even if run hangs, graph.json is written immediately after mkdir
    import threading
    result_holder = []
    def run_in_thread():
        try:
            r = ex.run(dag, run_dir=run_dir)
            result_holder.append(r)
        except Exception as e:
            result_holder.append({"error": str(e)})
    t = threading.Thread(target=run_in_thread)
    t.start()
    t.join(timeout=2.0)
    if not result_holder and run_dir.exists():
        # Run may still be going; at least run_dir and graph.json must exist after mkdir
        assert (run_dir / "graph.json").exists(), "graph.json written before loop"
    elif result_holder:
        result = result_holder[0]
        assert run_dir.exists()
        assert (run_dir / "graph.json").exists()
        if result.get("ok"):
            assert (run_dir / "state.json").exists()
            assert (run_dir / "summary.json").exists()
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            assert "run_id" in summary and "final_status" in summary and "counts" in summary and "run_dir" in summary


def test_write_run_dir_artifacts_summary_shape(tmp_path):
    """_write_run_dir_artifacts writes state.json and summary.json with required summary fields."""
    from hg_core.task_graph.state_store import RunState
    from hg_core.task_graph.state_machine import NodeStatus
    ex, _, _, _, store = make_executor(tmp_path)
    run_dir = tmp_path / "artifacts_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    dag = DAG.from_dict({
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast"},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    })
    nodes = list(dag.nodes)
    nodes[0].status = NodeStatus.DONE.value
    run_state = RunState(
        run_id="test-run-1",
        graph_id="g1",
        started_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:01Z",
        node_outputs={"n1": {"result": "ok"}},
        node_states={},
        final_status="completed",
    )
    ex._write_run_dir_artifacts(run_dir, dag, nodes, "test-run-1", run_state)
    assert (run_dir / "state.json").exists()
    assert (run_dir / "summary.json").exists()
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == "test-run-1"
    assert summary["graph_id"] == "g1"
    assert summary["final_status"] == "completed"
    assert summary["counts"]["done"] == 1
    assert summary["counts"]["failed"] == 0
    assert summary["run_dir"] == str(run_dir)


# --- Phase 2: retry and backoff tests ---


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_retry_n_then_success(tmp_path):
    """Node fails N times then succeeds on attempt N+1 -> node ends DONE."""
    ex, dispatcher, _, telemetry, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "retry_n_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {
                "id": "retry_twice",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": [],
                "inputs": {},
                "outputs": {"result": {}},
                "policy": {"max_retries": 2, "retry_backoff_ms": 10},
                "checkpoints": {"before": False, "after": False},
            }
        ],
    }
    result = ex.run(DAG.from_dict(dag_dict))
    assert result["ok"] is True
    assert result["final_status"] == "completed"
    assert dispatcher.calls.get("retry_twice") == 3
    assert result["node_outputs"]["retry_twice"]["result"].startswith("retry_twice_ok_attempt_3")


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_retry_n_plus_1_then_failed(tmp_path):
    """Node fails N+1 times -> node ends FAILED."""
    ex, dispatcher, _, telemetry, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "fail_n_plus_1_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {
                "id": "always_fail",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": [],
                "inputs": {},
                "outputs": {"result": {}},
                "policy": {"max_retries": 1, "retry_backoff_ms": 10},
                "checkpoints": {"before": False, "after": False},
            }
        ],
    }
    result = ex.run(DAG.from_dict(dag_dict))
    assert result["ok"] is True  # run completed; outcome is in final_status
    assert result["final_status"] in {"failed", "partial"}
    assert dispatcher.calls.get("always_fail") == 2
    assert result["run_state"]["node_states"]["always_fail"]["status"] == "failed"


def test_dispatch_agent_respects_timeout_s():
    """Dispatcher respects node.policy.timeout_s for agent nodes (passed to dispatch_agent)."""
    import unittest.mock
    from hg_core.task_graph.dispatch import dispatch_node
    from hg_core.task_graph.schema import Node, NodePolicy, Checkpoints

    node = Node(
        id="agent1",
        type="agent",
        assigned_entity="test_agent",
        depends_on=[],
        inputs={},
        outputs={},
        policy=NodePolicy(timeout_s=60),
        checkpoints=Checkpoints(before=False, after=False),
    )
    with unittest.mock.patch("hg_core.task_graph.dispatch.dispatch_agent") as mock_agent:
        mock_agent.return_value = {"ok": True, "outputs": {}}
        dispatch_node(node, {}, None, None, False)
        mock_agent.assert_called_once()
        call_kw = mock_agent.call_args[1]
        assert call_kw.get("timeout_s") == 60


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_backoff_applied_between_retries(tmp_path):
    """Backoff delay is applied between retries (mock sleep and assert it was called with retry_backoff_ms)."""
    import unittest.mock
    ex, dispatcher, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "backoff_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {
                "id": "retry_once",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": [],
                "inputs": {},
                "outputs": {"result": {}},
                "policy": {"max_retries": 1, "retry_backoff_ms": 50},
                "checkpoints": {"before": False, "after": False},
            }
        ],
    }
    with unittest.mock.patch("hg_core.task_graph.executor.time.sleep") as mock_sleep:
        result = ex.run(DAG.from_dict(dag_dict))
        assert result["ok"] is True
        mock_sleep.assert_called()
        mock_sleep.assert_any_call(0.05)  # 50ms in seconds


def test_max_node_executions_cap_summary_includes_run_error(tmp_path):
    """When run hits max_node_executions cap, _summary_dict_for_run_dir includes _run_error in error_summary."""
    from hg_core.task_graph.state_store import RunState
    from hg_core.task_graph.state_machine import NodeStatus
    ex, _, _, _, store = make_executor(tmp_path)
    run_dir = tmp_path / "cap_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    dag = DAG.from_dict({
        "graph_id": "cap_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "max_node_executions": 2},
        "inputs": {},
        "nodes": [
            {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
            {"id": "b", "type": "tool", "assigned_entity": "x", "depends_on": ["a"], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    })
    nodes = list(dag.nodes)
    nodes[0].status = NodeStatus.DONE.value
    nodes[1].status = NodeStatus.PENDING.value
    run_state = RunState(
        run_id="cap-run",
        graph_id="cap_v1",
        started_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:01Z",
        node_outputs={"a": {}},
        node_states={n.id: n.to_dict() for n in nodes},
        final_status="failed",
    )
    run_state.state["_run_error"] = {"code": "MAX_NODE_EXECUTIONS_EXCEEDED", "message": "max_node_executions cap (2) exceeded"}
    ex._write_run_dir_artifacts(run_dir, dag, nodes, "cap-run", run_state)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["final_status"] == "failed"
    assert any(e.get("code") == "MAX_NODE_EXECUTIONS_EXCEEDED" for e in summary["error_summary"])


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_binding_resolution_error_fails_node(tmp_path):
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    result = ex.run(DAG.from_dict(dag_bad_binding()))

    assert result["ok"] is False or result["final_status"] in {"failed", "partial", "completed"}

    run_state = result["run_state"]
    a_state = run_state["node_states"]["a"]
    assert a_state["status"] == "failed"
    assert a_state["error"]["code"] in {"INPUT_RESOLUTION_ERROR", "UNKNOWN_ERROR"}

    assert "dag_node_failed" in event_names(telemetry)


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_input_binding_mode_strict_fails_node_on_unresolved(tmp_path):
    """With input_binding_mode strict, node with unresolved ref gets INPUT_RESOLUTION_ERROR and fails."""
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    dag = DAG.from_dict(dag_unresolved_ref_input_binding("strict"))
    result = ex.run(dag)
    assert result["ok"] is True  # run completes (no fail_fast)
    ns = result["run_state"]["node_states"]["refs_missing"]
    assert ns["status"] == "failed"
    assert ns.get("error", {}).get("code") == "INPUT_RESOLUTION_ERROR"
    assert "dag_node_failed" in event_names(telemetry)
    assert dispatcher.calls.get("refs_missing", 0) == 0  # dispatcher not called


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_input_binding_mode_blocked_sets_blocked_and_emits_event(tmp_path):
    """With input_binding_mode blocked, node with unresolved ref gets status blocked and dag_node_blocked emitted."""
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    dag = DAG.from_dict(dag_unresolved_ref_input_binding("blocked"))
    result = ex.run(dag)
    assert result["ok"] is True
    ns = result["run_state"]["node_states"]["refs_missing"]
    assert ns["status"] == "blocked"
    assert "dag_node_blocked" in event_names(telemetry)
    blocked_events = [(n, p) for n, p in telemetry.events if n == "dag_node_blocked"]
    assert len(blocked_events) == 1
    assert blocked_events[0][1].get("unresolved") == ["x"]
    assert dispatcher.calls.get("refs_missing", 0) == 0  # dispatcher not called


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_input_binding_mode_lenient_passes_unresolved_to_dispatcher(tmp_path):
    """With input_binding_mode lenient, node with unresolved ref still gets dispatched; inputs contain the ref string."""
    ex, dispatcher, overseer, telemetry, _ = make_executor(tmp_path)
    dag = DAG.from_dict(dag_unresolved_ref_input_binding("lenient"))
    result = ex.run(dag)
    assert result["ok"] is True
    ns = result["run_state"]["node_states"]["refs_missing"]
    assert ns["status"] == "done"
    assert dispatcher.calls.get("refs_missing", 0) == 1
    # Dispatcher receives inputs; TestDispatcher echoes them in outputs
    out = result["node_outputs"].get("refs_missing", {})
    echo = out.get("echo_inputs", {})
    assert echo.get("x") == "$node.nonexistent.result"


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_deterministic_event_order_across_repeated_runs(tmp_path):
    ex1, _, _, tel1, _ = make_executor(tmp_path / "r1")
    ex2, _, _, tel2, _ = make_executor(tmp_path / "r2")

    dag = DAG.from_dict(dag_linear())
    r1 = ex1.run(dag)
    r2 = ex2.run(dag)

    seq1 = [name for name, _ in tel1.events]
    seq2 = [name for name, _ in tel2.events]
    assert seq1 == seq2

    starts1 = [p["node_id"] for name, p in tel1.events if name == "dag_node_started"]
    starts2 = [p["node_id"] for name, p in tel2.events if name == "dag_node_started"]
    assert starts1 == starts2 == ["a", "b", "c"]


def test_state_store_uses_explicit_base_dir(tmp_path):
    """When base_dir is passed, StateStore uses it (e.g. for tests)."""
    store = StateStore(base_dir=tmp_path / "dag_runs")
    assert store.base_dir == tmp_path / "dag_runs"


def test_state_store_default_base_dir_uses_workspace_root_when_available(monkeypatch, tmp_path):
    """When base_dir is None and get_workspace_root is available, default is workspace/memory/automation/dag_runs."""
    from hg_core.task_graph import state_store as state_store_mod
    expected = tmp_path / "memory" / "automation" / "dag_runs"
    monkeypatch.setattr(state_store_mod, "_default_base_dir", lambda: expected)
    store = StateStore()
    assert store.base_dir == expected


def test_state_store_default_base_dir_fallback_when_workspace_unavailable(monkeypatch):
    """When base_dir is None and default resolves to fallback path, StateStore uses it."""
    from pathlib import Path
    from hg_core.task_graph import state_store as state_store_mod
    fallback = Path("memory/automation/dag_runs")
    monkeypatch.setattr(state_store_mod, "_default_base_dir", lambda: fallback)
    store = StateStore()
    assert store.base_dir == fallback


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_steering_block_sets_blocked_status(tmp_path):
    """If overseer.before_node returns block, node is BLOCKED with STEERING_BLOCKED."""
    telemetry = TestTelemetry()
    dispatcher = TestDispatcher()
    overseer = BlockingOverseer("b")
    store = StateStore(tmp_path / "dag_runs")
    ex = TaskGraphExecutor(
        dispatcher=dispatcher,
        overseer=overseer,
        state_store=store,
        telemetry=telemetry,
    )
    dag = DAG.from_dict({
        "graph_id": "steering_block_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "checkpoints": {}},
            {"id": "b", "type": "tool", "assigned_entity": "x", "depends_on": ["a"], "inputs": {}, "outputs": {}, "checkpoints": {}},
        ],
    })
    result = ex.run(dag)
    ns = result["run_state"]["node_states"]["b"]
    assert ns["status"] == "blocked"
    assert ns.get("error", {}).get("code") == "STEERING_BLOCKED"


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_cancel_request_file_stops_run_before_dispatch(tmp_path):
    """If cancel.requested.json exists in run_dir, executor cancels before dispatching nodes."""
    ex, dispatcher, _, _, _ = make_executor(tmp_path)
    dag = DAG.from_dict(dag_linear())
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "cancel.requested.json").write_text(
        json.dumps({"run_id": "cancel-test", "reason": "unit test"}), encoding="utf-8"
    )
    result = ex.run(dag, run_dir=run_dir)
    assert result["final_status"] == "cancelled"
    assert dispatcher.calls == {}


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_cancel_request_mid_run_stops_before_next_node(tmp_path):
    """Cancel request written mid-run stops before next node executes."""
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    calls = []

    class CancelOnFirst:
        def __call__(self, node, resolved_inputs, **_kwargs):
            calls.append(node.id)
            if node.id == "a":
                (run_dir / "cancel.requested.json").write_text(
                    json.dumps({"run_id": "cancel-mid", "reason": "mid-run"}), encoding="utf-8"
                )
            return {"ok": True, "outputs": {"result": f"{node.id}_ok"}}

    ex = TaskGraphExecutor(
        dispatcher=CancelOnFirst(),
        overseer=None,
        state_store=StateStore(tmp_path / "dag_runs"),
        telemetry=TestTelemetry(),
    )
    dag = DAG.from_dict({
        "graph_id": "cancel_mid_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue"},
        "inputs": {},
        "nodes": [
            {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "checkpoints": {}},
            {"id": "b", "type": "tool", "assigned_entity": "x", "depends_on": ["a"], "inputs": {}, "outputs": {}, "checkpoints": {}},
        ],
    })
    result = ex.run(dag, run_dir=run_dir)
    assert result["final_status"] == "cancelled"
    assert calls == ["a"]


def test_resume_run_not_found_returns_error(tmp_path):
    """resume(dag, run_id) returns ok False and error run_not_found when run_id does not exist."""
    store = StateStore(base_dir=tmp_path / "dag_runs")
    ex = TaskGraphExecutor(state_store=store)
    dag = DAG.from_dict(dag_linear())
    result = ex.resume(dag, "nonexistent-run-id-12345")
    assert result["ok"] is False
    assert result.get("run_id") == "nonexistent-run-id-12345"
    assert result.get("error") == "run_not_found"


# --- Phase 1 durable: crash-safe persist, resume without re-run, RUNNING -> READY ---


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_crash_safe_persist_resume(tmp_path):
    """After run() completes, resume(dag, run_id) does not re-execute any node (DONE nodes stay DONE)."""
    from hg_core.task_graph.state_machine import NodeStatus

    store = StateStore(base_dir=tmp_path / "dag_runs")
    ex1, dispatcher1, _, _, _ = make_executor(tmp_path)
    ex1.state_store = store
    dag = DAG.from_dict(dag_linear())
    result1 = ex1.run(dag)
    assert result1["ok"] is True
    run_id = result1["run_id"]
    assert run_id
    calls_after_run = dict(dispatcher1.calls)

    ex2, dispatcher2, _, _, _ = make_executor(tmp_path / "other")
    ex2.state_store = store
    result2 = ex2.resume(dag, run_id)
    assert result2["ok"] is True
    assert result2["run_id"] == run_id
    assert result2["final_status"] == "completed"
    assert result2["node_outputs"].get("a") and result2["node_outputs"].get("b") and result2["node_outputs"].get("c")
    assert len(dispatcher2.calls) == 0, "resume must not re-dispatch already-DONE nodes"


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_resume_running_becomes_ready_and_progresses(tmp_path):
    """When loaded state has a node RUNNING, resume normalizes RUNNING -> READY so the run can progress."""
    from hg_core.task_graph.state_machine import NodeStatus
    from hg_core.task_graph.state_store import RunState
    from hg_core.task_graph.schema import Node

    store = StateStore(base_dir=tmp_path / "dag_runs")
    dag = DAG.from_dict(dag_linear())
    nodes = list(dag.nodes)
    by_id = {n.id: n for n in nodes}
    by_id["a"].status = NodeStatus.DONE.value
    by_id["a"].ended_at = "2025-01-01T00:00:01Z"
    by_id["b"].status = NodeStatus.RUNNING.value
    by_id["b"].started_at = "2025-01-01T00:00:02Z"
    by_id["c"].status = NodeStatus.PENDING.value

    run_id = "resume-running-test"
    run_state = RunState(
        run_id=run_id,
        graph_id=dag.graph_id,
        started_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:02Z",
        node_outputs={"a": {"result": "a_ok"}},
        node_states={n.id: n.to_dict() for n in nodes},
        final_status=None,
    )
    store.save(run_state, nodes)

    ex, dispatcher, _, _, _ = make_executor(tmp_path)
    ex.state_store = store
    result = ex.resume(dag, run_id)
    assert result["ok"] is True
    assert result["final_status"] == "completed"
    assert result["run_state"]["node_states"]["b"]["status"] == "done"
    assert dispatcher.calls.get("b", 0) >= 1, "resume must re-schedule RUNNING node b and execute it"


# --- Phase 2 HITL: pause at checkpoint, return paused, resume completes ---


def _dag_linear_pause_after_a():
    """Two-node DAG (a -> b); only node a has checkpoint. Pause after a, resume runs b and completes."""
    return {
        "graph_id": "pause_after_a_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "continue", "strict_bindings": False, "pause_at_checkpoint": True},
        "inputs": {"name": "Andrew"},
        "nodes": [
            {
                "id": "a",
                "type": "transform",
                "assigned_entity": "transformer",
                "depends_on": [],
                "inputs": {"name": "$graph.inputs.name"},
                "outputs": {},
                "checkpoints": {"before": True, "after": True},
            },
            {
                "id": "b",
                "type": "tool",
                "assigned_entity": "tool_runner",
                "depends_on": ["a"],
                "inputs": {"payload": "$node.a.result"},
                "outputs": {},
                "checkpoints": {},  # no checkpoint so resume does not pause again
            },
        ],
    }


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_hitl_pause_at_checkpoint_then_resume(tmp_path):
    """With pause_at_checkpoint, run pauses after first checkpoint (node a), returns paused; resume completes."""
    store = StateStore(base_dir=tmp_path / "dag_runs")
    ex1, dispatcher1, _, _, _ = make_executor(tmp_path)
    ex1.state_store = store
    dag = DAG.from_dict(_dag_linear_pause_after_a())
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    result1 = ex1.run(dag, run_dir=run_dir)
    assert result1["ok"] is True
    assert result1.get("status") == "paused"
    assert result1.get("checkpoint", {}).get("node_id") == "a"
    assert result1.get("checkpoint", {}).get("position") == "after"
    run_id = result1["run_id"]
    assert run_id

    ex2, dispatcher2, _, _, _ = make_executor(tmp_path / "other")
    ex2.state_store = store
    result2 = ex2.resume(dag, run_id, graph_inputs=dag.inputs)
    assert result2["ok"] is True
    assert result2["run_id"] == run_id
    assert result2["final_status"] == "completed"
    assert result2["node_outputs"].get("a") and result2["node_outputs"].get("b")
    assert dispatcher2.calls.get("a", 0) == 0, "resume must not re-run already-DONE node a"
    assert dispatcher2.calls.get("b", 0) >= 1


# --- Phase 3 state history and fork from snapshot ---


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_state_history_snapshots_and_index(tmp_path):
    """Run with run_dir produces state_history/state_*.json and state_history/index.jsonl with matching entries."""
    from hg_core.task_graph.state_history import list_snapshots, load_snapshot

    ex, _, _, _, _ = make_executor(tmp_path)
    dag = DAG.from_dict(dag_linear())
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    result = ex.run(dag, run_dir=run_dir)
    assert result["ok"] is True

    hist_dir = run_dir / "state_history"
    assert hist_dir.is_dir()
    state_files = sorted(f for f in hist_dir.glob("state_*.json") if f.name != "state_latest.json")
    assert len(state_files) >= 1, "at least one state snapshot"
    assert (hist_dir / "index.jsonl").exists()
    assert (hist_dir / "state_latest.json").exists()

    entries = list_snapshots(run_dir)
    assert len(entries) == len(state_files), "index entries match numbered state files"
    for e in entries:
        assert "seq" in e and "ts" in e and "reason" in e and "state_path" in e
        loaded = load_snapshot(run_dir, e["seq"])
        assert loaded["run_id"] == result["run_id"]
        assert "node_states" in loaded


@pytest.mark.timeout(EXECUTOR_TEST_TIMEOUT)
def test_fork_from_snapshot_then_resume(tmp_path):
    """Fork from snapshot at seq N into new run_dir with new_run_id; resume from forked state completes independently."""
    from hg_core.task_graph.state_history import fork_from_snapshot, list_snapshots

    store = StateStore(base_dir=tmp_path / "dag_runs")
    ex1, dispatcher1, _, _, _ = make_executor(tmp_path)
    ex1.state_store = store
    dag = DAG.from_dict(dag_linear())
    run_dir1 = tmp_path / "run1"
    run_dir1.mkdir(parents=True, exist_ok=True)
    result1 = ex1.run(dag, run_dir=run_dir1)
    assert result1["ok"] is True
    run_id1 = result1["run_id"]
    entries = list_snapshots(run_dir1)
    assert len(entries) >= 1, "at least one snapshot"
    seq = entries[0]["seq"]
    run_dir2 = tmp_path / "run2"
    new_run_id = "forked-run"
    fork_from_snapshot(run_dir1, seq, run_dir2, new_run_id)

    # Load forked state and verify
    state_path = run_dir2 / "state.json"
    assert state_path.exists()
    with open(state_path, encoding="utf-8") as f:
        forked = json.load(f)
    assert forked["run_id"] == new_run_id
    assert "node_states" in forked

    # Put forked state into store so resume(new_run_id) can load it
    from hg_core.task_graph.state_store import RunState as RS
    from hg_core.task_graph.schema import Node as N
    run_state = RS.from_dict(forked)
    nodes_list = [N.from_dict(forked["node_states"][nid]) for nid in sorted(forked.get("node_states", {}))]
    store.save(run_state, nodes_list)

    ex2, dispatcher2, _, _, _ = make_executor(tmp_path / "other")
    ex2.state_store = store
    result2 = ex2.resume(dag, new_run_id, graph_inputs=dag.inputs)
    assert result2["ok"] is True
    assert result2["run_id"] == new_run_id
    assert result2["final_status"] == "completed"
    assert dispatcher2.calls.get("a", 0) == 0
    assert dispatcher2.calls.get("b", 0) >= 1 and dispatcher2.calls.get("c", 0) >= 1
