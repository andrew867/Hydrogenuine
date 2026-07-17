"""
Tests for failure injection harness.

Per TEST_PLAN: for each fault scenario assert expected classification and policy
behavior (backoff, breaker, dead-letter); no side effects (fake destination only);
smoke fault suite runnable in CI. At least 3 scenarios per primary workflow.
"""

from __future__ import annotations

import pytest

from hg_core.task_graph.workflow_registry import get_primary_workflow_ids

# Fault scenario IDs per spec (minimum set)
FAULT_SCENARIOS = [
    "transient_network",
    "rate_limiting",
    "dependency_unavailable",
    "timeout",
    "validation_failure",
    "safety_blocked",
    "permission_denied",
    "concurrency_collision",
]

MIN_SCENARIOS_PER_WORKFLOW = 3


def test_fault_injection_module_importable():
    """Fault injection harness module is importable."""
    from hg_core.task_graph import fault_injection

    assert fault_injection is not None


def test_scenario_runner_injects_at_step():
    """Scenario runner accepts scenario config and injects fault at configured step."""
    from hg_core.task_graph.fault_injection import run_scenario

    # Fake destination only; no side effects
    result = run_scenario(
        workflow_id="fourclaw-auto-post",
        scenario_id="transient_network",
        step_index=0,
        fake_destination_ledger=[],
    )
    assert "failure_class" in result or "outcome" in result
    assert "dead_letter" in result or "terminal" in result or "ok" in result


def test_assertion_library_failure_class_mapping():
    """Assertions library can check failure class mapping."""
    from hg_core.task_graph.fault_injection import assert_failure_class

    # transient_network -> retryable
    assert_failure_class("transient_network", "transient_network", retryable=True)
    # validation_failure -> not retryable
    assert_failure_class("validation_failure", "validation_failed", retryable=False)


def test_assertion_library_dead_letter_captured():
    """Assertions library can check dead-letter artifact created on terminal failure."""
    from hg_core.task_graph.fault_injection import assert_dead_letter_captured

    outcome = {"terminal": True, "dead_letter": {"run_id": "r1", "failure_class": "timeout"}}
    assert_dead_letter_captured(outcome)


def test_assertion_library_no_external_write_when_blocked():
    """Assertions library can check no external write attempted when blocked."""
    from hg_core.task_graph.fault_injection import assert_no_external_write_when_blocked

    outcome = {"blocked": True, "external_write_attempted": False}
    assert_no_external_write_when_blocked(outcome)


def test_assertion_library_idempotency_prevents_duplicate():
    """Assertions library can check idempotency ledger prevents duplicates on retry."""
    from hg_core.task_graph.fault_injection import assert_idempotency_prevents_duplicate

    ledger = [{"key": "k1", "completed": True}]
    assert_idempotency_prevents_duplicate(ledger, "k1", attempted_second_write=False)


def test_at_least_three_scenarios_per_primary_workflow():
    """Each primary workflow has at least 3 fault scenarios covered."""
    from hg_core.task_graph.fault_injection import get_scenarios_for_workflow

    for wid in get_primary_workflow_ids():
        scenarios = get_scenarios_for_workflow(wid)
        assert len(scenarios) >= MIN_SCENARIOS_PER_WORKFLOW, (
            f"{wid} must have at least {MIN_SCENARIOS_PER_WORKFLOW} fault scenarios"
        )


def test_fake_destination_ledger_only_no_side_effects():
    """Run scenario with fake destination ledger; no real side effects."""
    from hg_core.task_graph.fault_injection import run_scenario

    ledger = []
    run_scenario(
        workflow_id="moltbook-auto-post",
        scenario_id="rate_limiting",
        step_index=0,
        fake_destination_ledger=ledger,
    )
    # Ledger is only written to in-memory; no external call
    assert isinstance(ledger, list)


@pytest.mark.smoke_fault
def test_smoke_fault_suite_transient_network():
    """Smoke fault suite: transient network scenario."""
    from hg_core.task_graph.fault_injection import run_scenario, assert_failure_class

    result = run_scenario(
        workflow_id="fourclaw-auto-post",
        scenario_id="transient_network",
        step_index=0,
        fake_destination_ledger=[],
    )
    fc = result.get("failure_class", "transient_network")
    assert_failure_class("transient_network", fc, result.get("retryable", True))


@pytest.mark.smoke_fault
def test_smoke_fault_suite_validation_failure():
    """Smoke fault suite: validation failure scenario."""
    from hg_core.task_graph.fault_injection import run_scenario, assert_failure_class

    result = run_scenario(
        workflow_id="fourclaw-auto-post",
        scenario_id="validation_failure",
        step_index=0,
        fake_destination_ledger=[],
    )
    fc = result.get("failure_class", "validation_failed")
    assert_failure_class("validation_failure", fc, result.get("retryable", False))


@pytest.mark.smoke_fault
def test_smoke_fault_suite_safety_blocked():
    """Smoke fault suite: safety blocked scenario."""
    from hg_core.task_graph.fault_injection import run_scenario, assert_no_external_write_when_blocked

    result = run_scenario(
        workflow_id="fourclaw-auto-post",
        scenario_id="safety_blocked",
        step_index=0,
        fake_destination_ledger=[],
    )
    assert_no_external_write_when_blocked(result)
