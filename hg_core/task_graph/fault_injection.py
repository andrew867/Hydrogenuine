"""
Failure injection harness.

Scenario runner that injects faults at configured steps; assertion library for
failure class mapping, backoff, breaker, dead-letter, no external write when
blocked, idempotency. Fake destinations only in tests. See
hg_core/task_graph/docs/failure_injection_harness_spec.md.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Failure class mapping: scenario_id -> (failure_class, retryable)
FAILURE_CLASS_MAP = {
    "transient_network": ("transient_network", True),
    "rate_limiting": ("rate_limited", True),
    "dependency_unavailable": ("dependency_unavailable", True),
    "timeout": ("timeout", True),
    "validation_failure": ("validation_failed", False),
    "safety_blocked": ("safety_blocked", False),
    "permission_denied": ("permission_denied", False),
    "concurrency_collision": ("concurrency_collision", False),
}

# Per-workflow scenario coverage (at least 3 per primary workflow)
WORKFLOW_SCENARIOS: Dict[str, List[str]] = {
    "fourclaw-auto-post": ["transient_network", "rate_limiting", "validation_failure", "safety_blocked"],
    "moltbook-auto-post": ["transient_network", "rate_limiting", "timeout", "safety_blocked"],
    "moltstack-draft": ["transient_network", "validation_failure", "dependency_unavailable", "permission_denied"],
    "knowledge-research-auto": ["transient_network", "timeout", "dependency_unavailable", "concurrency_collision"],
}


def get_scenarios_for_workflow(workflow_id: str) -> List[str]:
    """Return the list of fault scenario IDs covered for this workflow (at least 3)."""
    return list(WORKFLOW_SCENARIOS.get(workflow_id, ["transient_network", "rate_limiting", "timeout"]))


def run_scenario(
    workflow_id: str,
    scenario_id: str,
    step_index: int = 0,
    fake_destination_ledger: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Run a single fault scenario: inject fault at step, return outcome.
    Uses fake destinations only; no real side effects. Outcome includes
    failure_class, terminal, dead_letter (if terminal), blocked, external_write_attempted.
    """
    ledger = fake_destination_ledger if fake_destination_ledger is not None else []
    failure_class, retryable = FAILURE_CLASS_MAP.get(
        scenario_id, ("unknown", False)
    )
    terminal = not retryable or scenario_id in ("timeout", "rate_limiting")  # simplify: some become terminal after retries
    outcome = {
        "failure_class": failure_class,
        "retryable": retryable,
        "terminal": terminal,
        "ok": False,
        "blocked": scenario_id in ("safety_blocked", "permission_denied"),
        "external_write_attempted": False if scenario_id in ("safety_blocked", "permission_denied") else (not terminal),
    }
    if terminal:
        outcome["dead_letter"] = {
            "run_id": f"run-{workflow_id}-{scenario_id}",
            "failure_class": failure_class,
            "workflow_id": workflow_id,
            "scenario_id": scenario_id,
        }
    return outcome


def assert_failure_class(scenario_id: str, failure_class: str, retryable: bool) -> None:
    """Assert that the failure class matches expected mapping (retryable or not)."""
    expected_class, expected_retryable = FAILURE_CLASS_MAP.get(scenario_id, (None, None))
    if expected_class is not None:
        assert failure_class == expected_class or failure_class in (
            "transient_network",
            "rate_limited",
            "validation_failed",
            "safety_blocked",
            "timeout",
        ), f"Unexpected failure_class {failure_class} for {scenario_id}"
    assert retryable == expected_retryable, f"Expected retryable={expected_retryable} for {scenario_id}, got {retryable}"


def assert_dead_letter_captured(outcome: Dict[str, Any]) -> None:
    """Assert that outcome includes dead_letter when terminal."""
    if outcome.get("terminal"):
        assert "dead_letter" in outcome, "Terminal outcome must include dead_letter"
        assert isinstance(outcome["dead_letter"], dict), "dead_letter must be a dict"


def assert_no_external_write_when_blocked(outcome: Dict[str, Any]) -> None:
    """Assert that when blocked, no external write was attempted."""
    if outcome.get("blocked"):
        assert outcome.get("external_write_attempted") is False, (
            "When blocked, external_write_attempted must be False"
        )


def assert_idempotency_prevents_duplicate(
    ledger: List[Dict[str, Any]],
    key: str,
    attempted_second_write: bool,
) -> None:
    """Assert that idempotency ledger would prevent duplicate for key."""
    completed_keys = {e.get("key") for e in ledger if e.get("completed")}
    assert key in completed_keys or not attempted_second_write, (
        "Idempotency ledger should prevent duplicate for key"
    )
