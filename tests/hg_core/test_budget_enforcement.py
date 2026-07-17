"""Tests for DAG effect budgets and enforcement."""

import tempfile
from pathlib import Path

import pytest

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    TaskGraphExecutor,
)
from hg_core.task_graph.effects import Budget, get_budgets
from hg_core.task_graph.budget_enforcer import (
    BUDGET_EXCEEDED_CODE,
    apply_after_dispatch,
    check_before_dispatch,
)


def test_get_budgets_parses_run_policy():
    """get_budgets parses run_policy.budgets into Budget instances."""
    run_policy = {
        "budgets": {
            "dispatch_attempts": {"limit": 3, "hard": True, "scope": "run"},
            "tokens": {"limit": 1000.0, "hard": False, "on_exceed": "pause"},
        }
    }
    budgets = get_budgets(run_policy)
    assert "dispatch_attempts" in budgets
    assert isinstance(budgets["dispatch_attempts"], Budget)
    assert budgets["dispatch_attempts"].limit == 3.0
    assert budgets["dispatch_attempts"].hard is True
    assert budgets["dispatch_attempts"].scope == "run"
    assert budgets["tokens"].limit == 1000.0
    assert budgets["tokens"].hard is False
    assert budgets["tokens"].on_exceed == "pause"


def test_get_budgets_empty_when_no_budgets():
    """get_budgets returns empty dict when run_policy has no budgets."""
    assert get_budgets({}) == {}
    assert get_budgets({"budgets": None}) == {}
    assert get_budgets({"budgets": {}}) == {}


def test_apply_after_dispatch_updates_budget_used():
    """apply_after_dispatch increments run_state.budget_used from observed usage."""
    run_policy = {}
    run_state = {}
    apply_after_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
    assert run_state["budget_used"]["dispatch_attempts"] == 1.0

    apply_after_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
    assert run_state["budget_used"]["dispatch_attempts"] == 2.0

    apply_after_dispatch(run_policy, run_state, {"tokens": 100})
    assert run_state["budget_used"]["tokens"] == 100.0
    assert run_state["budget_used"]["dispatch_attempts"] == 2.0


def test_check_before_dispatch_allows_when_under_limit():
    """check_before_dispatch returns (True, None) when projected usage is under limit."""
    run_policy = {"budgets": {"dispatch_attempts": {"limit": 3, "hard": True}}}
    run_state = {"budget_used": {"dispatch_attempts": 1}}
    allowed, err = check_before_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
    assert allowed is True
    assert err is None


def test_check_before_dispatch_denies_when_exceeds():
    """check_before_dispatch returns (False, error_dict) when projected usage exceeds limit."""
    run_policy = {"budgets": {"dispatch_attempts": {"limit": 3, "hard": True}}}
    run_state = {"budget_used": {"dispatch_attempts": 3}}
    allowed, err = check_before_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
    assert allowed is False
    assert err is not None
    assert err["code"] == BUDGET_EXCEEDED_CODE
    assert err["budget"] == "dispatch_attempts"
    assert err["limit"] == 3.0
    assert err["would_be"] == 4.0


def _budget_node(nid: str, max_retries: int = 3) -> Node:
    return Node(
        id=nid,
        type="eval",
        assigned_entity="evaluator",
        depends_on=[],
        inputs={"expression": "1 + 1", "output_key": "x"},
        outputs={},
        policy=NodePolicy(max_retries=max_retries),
        checkpoints=Checkpoints(),
    )


def test_budget_exceeded_fails_run():
    """Cap dispatch_attempts at 3; DAG that needs 4 attempts (retries) fails with BUDGET_EXCEEDED."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = DAG(
            graph_id="budget_test",
            version="1.0",
            run_policy=RunPolicy(
                max_concurrency=1,
                failure_mode="fail_fast",
                budgets={"dispatch_attempts": {"limit": 3, "hard": True, "scope": "run"}},
            ),
            inputs={},
            nodes=[_budget_node("a", max_retries=5)],
        )
        # Dispatcher always fails so node is retried; after 3 dispatches budget is exceeded, 4th is blocked
        def failing_dispatcher(node, inputs, **kwargs):
            return {"ok": False, "error": {"code": "FAIL", "message": "mock failure"}}

        executor = TaskGraphExecutor(dispatcher=failing_dispatcher)
        summary = executor.run(dag, run_dir=run_dir, run_id="run-budget")
        assert summary.get("ok") is False
        assert summary.get("final_status") == "failed"
        run_error = summary.get("run_state", {}).get("state", {}).get("_run_error")
        assert run_error is not None
        assert run_error.get("code") == BUDGET_EXCEEDED_CODE


def test_dispatcher_tokens_increment_budget_used():
    """Dispatcher response with tokens increments budget_used.tokens."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = DAG(
            graph_id="budget_tokens",
            version="1.0",
            run_policy=RunPolicy(
                max_concurrency=1,
                failure_mode="fail_fast",
                budgets={
                    "dispatch_attempts": {"limit": 10, "hard": True},
                    "tokens": {"limit": 500, "hard": True},
                },
            ),
            inputs={},
            nodes=[_budget_node("a", max_retries=0)],
        )

        def dispatcher_with_tokens(node, inputs, **kwargs):
            return {"ok": True, "outputs": {"x": 2}, "tokens": 100}

        executor = TaskGraphExecutor(dispatcher=dispatcher_with_tokens)
        summary = executor.run(dag, run_dir=run_dir, run_id="run-tokens")
        assert summary.get("ok") is True
        budget_used = summary.get("run_state", {}).get("state", {}).get("budget_used", {})
        assert budget_used.get("tokens") == 100
        assert budget_used.get("dispatch_attempts") == 1


def test_dispatcher_external_calls_increment_budget_used():
    """Dispatcher response with external_calls (or tool dispatch) increments budget_used.external_calls."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = DAG(
            graph_id="budget_external",
            version="1.0",
            run_policy=RunPolicy(
                max_concurrency=1,
                failure_mode="fail_fast",
                budgets={
                    "dispatch_attempts": {"limit": 10, "hard": True},
                    "external_calls": {"limit": 5, "hard": True},
                },
            ),
            inputs={},
            nodes=[_budget_node("a", max_retries=0)],
        )

        def dispatcher_with_external(node, inputs, **kwargs):
            return {"ok": True, "outputs": {"x": 1}, "external_calls": 1}

        executor = TaskGraphExecutor(dispatcher=dispatcher_with_external)
        summary = executor.run(dag, run_dir=run_dir, run_id="run-external")
        assert summary.get("ok") is True
        budget_used = summary.get("run_state", {}).get("state", {}).get("budget_used", {})
        assert budget_used.get("external_calls") == 1


def test_summary_json_contains_budget_used():
    """Run with budgets set; summary.json (via run_dir) contains budget_used."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = DAG(
            graph_id="budget_summary",
            version="1.0",
            run_policy=RunPolicy(
                max_concurrency=1,
                failure_mode="fail_fast",
                budgets={"dispatch_attempts": {"limit": 10, "hard": True}},
            ),
            inputs={},
            nodes=[_budget_node("a", max_retries=0)],
        )
        def ok_dispatcher(node, inputs, **kwargs):
            return {"ok": True, "outputs": {"x": 1}}
        executor = TaskGraphExecutor(dispatcher=ok_dispatcher)
        executor.run(dag, run_dir=run_dir, run_id="run-summary")
        summary_path = run_dir / "summary.json"
        assert summary_path.exists()
        import json
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        assert "budget_used" in summary_data
        assert summary_data["budget_used"].get("dispatch_attempts") == 1


def test_events_jsonl_has_budget_events():
    """Run with run_dir; events.jsonl has budget_updated (and budget_exceeded when applicable)."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = DAG(
            graph_id="budget_events",
            version="1.0",
            run_policy=RunPolicy(
                max_concurrency=1,
                failure_mode="fail_fast",
                budgets={"dispatch_attempts": {"limit": 10, "hard": True}},
            ),
            inputs={},
            nodes=[_budget_node("a", max_retries=0)],
        )
        def ok_dispatcher(node, inputs, **kwargs):
            return {"ok": True, "outputs": {"x": 1}}
        executor = TaskGraphExecutor(dispatcher=ok_dispatcher)
        executor.run(dag, run_dir=run_dir, run_id="run-events")
        events_path = run_dir / "events.jsonl"
        assert events_path.exists()
        lines = [ln.strip() for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        import json
        events = [json.loads(ln) for ln in lines]
        event_names = [e.get("event") for e in events]
        assert "budget_updated" in event_names
