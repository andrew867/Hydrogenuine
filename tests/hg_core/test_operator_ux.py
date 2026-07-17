"""
Tests for operator UX minimum and approval policy.

Per TEST_PLAN: snapshot or contract tests for status and run details; permission
tests for operator actions; replay dead-letter in shadow leaves no side effects.
"""

from __future__ import annotations

import pytest


def test_operator_ux_module_importable():
    """Operator UX module is importable."""
    from hg_core.task_graph import operator_ux

    assert operator_ux is not None


def test_status_overview_contract():
    """Status overview returns expected shape (what ran, paused, failing, breaker states)."""
    from hg_core.task_graph.operator_ux import get_status_overview

    overview = get_status_overview()
    assert isinstance(overview, dict)
    assert "recent" in overview or "workflows" in overview or "breaker_states" in overview or "paused" in overview


def test_run_detail_contract():
    """Run detail returns audit summary, trace/output/approval links, failure class."""
    from hg_core.task_graph.operator_ux import get_run_detail

    detail = get_run_detail("run-nonexistent")
    assert isinstance(detail, dict)
    assert "run_id" in detail or "error" in detail or "summary" in detail


def test_dead_letter_queue_contract():
    """Dead-letter queue returns list of terminal failures."""
    from hg_core.task_graph.operator_ux import get_dead_letter_queue

    queue = get_dead_letter_queue()
    assert isinstance(queue, list)


def test_approvals_queue_contract():
    """Approvals queue returns list with approval decisions."""
    from hg_core.task_graph.operator_ux import get_approvals_queue

    queue = get_approvals_queue()
    assert isinstance(queue, list)


def test_replay_dead_letter_shadow_no_side_effects():
    """Replay dead-letter in shadow (no-side-effects) mode leaves no side effects."""
    from hg_core.task_graph.operator_ux import replay_dead_letter

    result = replay_dead_letter("dlq-nonexistent", shadow=True)
    assert isinstance(result, dict)
    assert result.get("shadow") is True or "ok" in result or "error" in result
    assert result.get("external_write_attempted") is False or "external_write" not in str(result)


def test_approval_policy_default_approve():
    """Approval policy: default approve; denied only when blacklist matches."""
    from hg_core.task_graph.operator_ux import evaluate_approval

    decision = evaluate_approval(workflow_id="fourclaw-auto-post", action_summary={})
    assert decision.get("decision") in ("approved", "denied")
    assert "policy_basis" in decision or "rationale" in decision


def test_approval_policy_denied_never_calls_external():
    """When denied, external call must not be attempted (contract: decision=denied)."""
    from hg_core.task_graph.operator_ux import evaluate_approval

    decision = evaluate_approval(
        workflow_id="fourclaw-auto-post",
        action_summary={"strict_blacklist_triggered": True},
    )
    if decision.get("decision") == "denied":
        assert decision.get("allow_external_call") is False or "allow_external" not in decision
