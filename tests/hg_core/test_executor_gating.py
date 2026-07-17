"""
Chapter 1.5: gating wired in executor — APPROVAL_REQUESTED on deny, allow proceeds.
See .cursor/plans/stickyreality/chapter1_5_completion/TESTS/00_test_plan.md.
"""

from __future__ import annotations

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import patch

from hg_core.task_graph.schema import DAG
from hg_core.ledger import iterate_events
from tests.test_task_graph_executor import make_executor


def test_executor_gate_deny_emits_approval_requested(tmp_path: Path):
    """Policy denies (e.g. budget=0); run one-node DAG; node not successful; ledger has APPROVAL_REQUESTED."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "policy").mkdir(parents=True, exist_ok=True)
    policy_yaml = tmp_path / "artifacts" / "policy" / "trust_and_budget_policy.yaml"
    policy_yaml.write_text(
        "version: v1\nbudget:\n  default_limit: 0\n  hard: true\naction_costs:\n  READ: 0.1\n  WRITE: 1.0\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "run_gate_deny"
    ex, _, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "eval", "assigned_entity": "system", "depends_on": [], "inputs": {"expression": "1"}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    result = ex.run(dag, run_dir=run_dir)
    assert result.get("ok") is False or result.get("final_status") == "failed" or any(
        n.get("status") == "failed" for n in (result.get("node_states") or {}).values()
    )
    evs = list(iterate_events(tmp_path))
    actions = [e["action"] for e in evs]
    assert "APPROVAL_REQUESTED" in actions


def test_executor_gate_allow_proceeds(tmp_path: Path):
    """Policy allows; run one-node DAG; node completes; no APPROVAL_REQUESTED for that node."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "run_gate_allow"
    ex, _, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "eval", "assigned_entity": "system", "depends_on": [], "inputs": {"expression": "1"}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    result = ex.run(dag, run_dir=run_dir)
    assert result.get("ok") is True
    evs = list(iterate_events(tmp_path))
    approval_evs = [e for e in evs if e.get("action") == "APPROVAL_REQUESTED" and (e.get("payload") or {}).get("node_id") == "n1"]
    assert len(approval_evs) == 0


def test_executor_optional_ledger_failure_logs_run_completes(tmp_path: Path, caplog):
    """When ledger emit fails inside lifecycle, run still completes and a log is emitted (exception visibility)."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "run_ledger_fail"
    ex, _, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "eval", "assigned_entity": "system", "depends_on": [], "inputs": {"expression": "1"}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    with patch("hg_core.ledger.emit", side_effect=RuntimeError("ledger unavailable")):
        with caplog.at_level(logging.DEBUG):
            result = ex.run(dag, run_dir=run_dir)
    assert result.get("ok") is True
    assert "run_id" in result
    assert "Ledger" in caplog.text or "ledger" in caplog.text
