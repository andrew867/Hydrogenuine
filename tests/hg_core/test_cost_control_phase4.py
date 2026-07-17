"""Tests for autonomy Phase 4: cost control (K1–K4)."""

import json
import pytest
from pathlib import Path

from hg_core.task_graph.budget_enforcer import (
    check_before_dispatch,
    apply_after_dispatch,
    BUDGET_EXCEEDED_CODE,
)
from hg_core.task_graph.cost_accounting import (
    trace_budget_fields,
    aggregate_daily,
    get_daily_aggregation,
)


# --- K1/K2: Budget and backpressure ---


def test_budget_accounting_over_budget_denied():
    """When projected usage would exceed limit, check_before_dispatch denies."""
    run_policy = {"budgets": {"tokens": {"limit": 100, "hard": True}}}
    run_state = {"budget_used": {"tokens": 95}}
    allowed, err = check_before_dispatch(run_policy, run_state, {"tokens": 10})
    assert allowed is False
    assert err is not None
    assert err.get("code") == BUDGET_EXCEEDED_CODE


def test_budget_accounting_under_budget_allowed():
    """When under limit, check_before_dispatch allows."""
    run_policy = {"budgets": {"tokens": {"limit": 100, "hard": True}}}
    run_state = {"budget_used": {"tokens": 50}}
    allowed, err = check_before_dispatch(run_policy, run_state, {"tokens": 10})
    assert allowed is True
    assert err is None


def test_apply_after_dispatch_increments_budget_used():
    """apply_after_dispatch increments run_state.budget_used."""
    run_policy = {}
    run_state = {}
    apply_after_dispatch(run_policy, run_state, {"tokens": 100})
    assert run_state["budget_used"]["tokens"] == 100.0
    apply_after_dispatch(run_policy, run_state, {"tokens": 50})
    assert run_state["budget_used"]["tokens"] == 150.0


# --- K3: Trace budget fields and daily aggregation ---


def test_trace_budget_fields():
    """trace_budget_fields returns budget_used, budget_remaining, budget_limits."""
    budget_used = {"tokens": 80, "dispatch_attempts": 3}
    budget_limits = {"tokens": 100, "dispatch_attempts": 10}
    out = trace_budget_fields(budget_used, budget_limits)
    assert out["budget_used"] == {"tokens": 80, "dispatch_attempts": 3}
    assert out["budget_remaining"]["tokens"] == 20.0
    assert out["budget_remaining"]["dispatch_attempts"] == 7.0


def test_daily_aggregation(tmp_path):
    """aggregate_daily appends to daily file; get_daily_aggregation returns workflows and runs."""
    aggregate_daily(tmp_path, "workflow-a", "run-1", {"tokens": 100})
    aggregate_daily(tmp_path, "workflow-a", "run-2", {"tokens": 50})
    data = get_daily_aggregation(tmp_path)
    assert "workflows" in data
    assert "workflow-a" in data["workflows"]
    assert data["workflows"]["workflow-a"]["tokens"] == 150.0
    assert len(data.get("runs", [])) >= 2


# --- K4: Retries same bucket (conceptual: budget_used is shared across retries in executor) ---


def test_retries_consume_same_bucket():
    """Simulate: multiple dispatch attempts (retries) increment same budget_used; cap enforced."""
    run_policy = {"budgets": {"dispatch_attempts": {"limit": 5, "hard": True}}}
    run_state = {"budget_used": {}}
    for _ in range(5):
        allowed, _ = check_before_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
        assert allowed is True
        apply_after_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
    assert run_state["budget_used"]["dispatch_attempts"] == 5.0
    allowed, err = check_before_dispatch(run_policy, run_state, {"dispatch_attempts": 1})
    assert allowed is False
    assert err is not None
    assert err.get("code") == BUDGET_EXCEEDED_CODE
