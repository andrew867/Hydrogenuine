"""
Chapter 1.5: escrow lifecycle — ESCROW_LOCKED before high-impact, RELEASED/SLASHED after.
See .cursor/plans/stickyreality/chapter1_5_completion/TESTS/00_test_plan.md.
"""

from __future__ import annotations

import unittest.mock
import pytest
from pathlib import Path

from hg_core.task_graph.schema import DAG
from hg_core.ledger import iterate_events
from tests.test_task_graph_executor import make_executor


def test_escrow_locked_emitted_before_high_impact(tmp_path: Path):
    """Run with one high-impact (agent) node; assert ESCROW_LOCKED before action with correct amount."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "policy").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "policy" / "trust_and_budget_policy.yaml").write_text(
        "version: v1\nbudget:\n  default_limit: 100\n  hard: true\nescrow:\n  lock_amount_default: 5.0\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "run_escrow"
    ex, _, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "agent1", "type": "agent", "assigned_entity": "test_task", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    with unittest.mock.patch("hg_core.task_graph.dispatch.dispatch_agent") as mock_agent:
        mock_agent.return_value = {"ok": True, "outputs": {}}
        ex.run(dag, run_dir=run_dir)
    evs = list(iterate_events(tmp_path))
    locked = [e for e in evs if e.get("action") == "ESCROW_LOCKED"]
    assert len(locked) >= 1
    assert locked[0]["payload"].get("amount") == 5.0
    assert locked[0]["payload"].get("run_id")


def test_escrow_released_on_success_slashed_on_failure(tmp_path: Path):
    """Success run: ESCROW_RELEASED after; failure run: ESCROW_SLASHED after; amounts match lock."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "policy").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "policy" / "trust_and_budget_policy.yaml").write_text(
        "version: v1\nbudget:\n  default_limit: 100\n  hard: true\nescrow:\n  lock_amount_default: 10.0\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "run_escrow_ok"
    ex, _, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "agent1", "type": "agent", "assigned_entity": "test_task", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    with unittest.mock.patch("hg_core.task_graph.dispatch.dispatch_agent") as mock_agent:
        mock_agent.return_value = {"ok": True, "outputs": {}}
        ex.run(dag, run_dir=run_dir)
    evs = list(iterate_events(tmp_path))
    released = [e for e in evs if e.get("action") == "ESCROW_RELEASED"]
    assert len(released) >= 1
    assert released[0]["payload"].get("amount") == 10.0

    # Failure case: new workspace to get clean ledger
    tmp2 = tmp_path / "fail_run"
    tmp2.mkdir()
    (tmp2 / "memory").mkdir(parents=True, exist_ok=True)
    (tmp2 / "artifacts" / "policy").mkdir(parents=True, exist_ok=True)
    (tmp2 / "artifacts" / "policy" / "trust_and_budget_policy.yaml").write_text(
        "version: v1\nbudget:\n  default_limit: 100\n  hard: true\nescrow:\n  lock_amount_default: 7.0\n",
        encoding="utf-8",
    )
    run_dir_fail = tmp2 / "memory" / "automation" / "dag_runs" / "run_escrow_fail"
    ex2, _, _, _, _ = make_executor(tmp2)
    dag_fail = DAG.from_dict({
        **dag_dict,
        "nodes": [
            {"id": "agent1", "type": "agent", "assigned_entity": "test_task", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {"max_retries": 0}, "checkpoints": {}},
        ],
    })
    from hg_core.task_graph.dispatch import dispatch_node as _real_dispatch_node
    def _failing_dispatcher(node, resolved_inputs, **kwargs):
        if getattr(node, "type", None) == "agent":
            return {"ok": False, "error": {"code": "FAILED", "message": "simulated"}}
        return _real_dispatch_node(node, resolved_inputs, **kwargs)
    ex2.dispatcher = _failing_dispatcher
    ex2.run(dag_fail, run_dir=run_dir_fail)
    evs_fail = list(iterate_events(tmp2))
    slashed = [e for e in evs_fail if e.get("action") == "ESCROW_SLASHED"]
    assert len(slashed) >= 1
    assert slashed[0]["payload"].get("amount") == 7.0
