"""SIM offline deterministic rehearsal — predicted success is not permission."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_core.runtime_context.config import sim_offline_only, sim_refuse_stale_scenario
from hg_core.runtime_context.errors import (
    REFUSED_EVENT_HEAD_DRIFT,
    REFUSED_EXPIRED_SCENARIO,
    REFUSED_FORBIDDEN_ACTION_IN_SCENARIO,
    REFUSED_PREDICTION_AS_TRUTH,
    REFUSED_SIMULATION_AS_PERMISSION,
    REFUSED_STALE_SCENARIO,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.simulated_outcome_rehearsal.types import SimulationScenario, scenario_from_fixture

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def refuse_simulation_success_as_permission(*, treat_as_permit: bool) -> None:
    if treat_as_permit:
        raise RuntimeContextValidationError(
            REFUSED_SIMULATION_AS_PERMISSION,
            "simulated success cannot be treated as permission or authority",
        )


def refuse_prediction_as_truth(*, treat_as_truth: bool) -> None:
    if treat_as_truth:
        raise RuntimeContextValidationError(
            REFUSED_PREDICTION_AS_TRUTH,
            "predicted outcome cannot be treated as truth or permission",
        )


def evaluate_scenario(
    scenario: SimulationScenario,
    *,
    observed_at: str,
    expected_event_head: Optional[str] = None,
) -> dict[str, object]:
    """Offline deterministic rehearsal; simulation is not reality."""
    if sim_offline_only() and any(step.startswith("live_") for step in scenario.simulated_steps):
        raise RuntimeContextValidationError(
            "sim.refused.live_planning",
            "offline-only mode refuses live model planning steps",
        )
    if observed_at > scenario.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_SCENARIO,
            "scenario_id": scenario.scenario_id,
            "simulation_success_is_permission": False,
        }
    if sim_refuse_stale_scenario() and observed_at < scenario.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_SCENARIO,
            "scenario_id": scenario.scenario_id,
            "simulation_success_is_permission": False,
        }
    if expected_event_head and expected_event_head != scenario.starting_event_head:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EVENT_HEAD_DRIFT,
            "scenario_id": scenario.scenario_id,
            "simulation_success_is_permission": False,
        }
    if scenario.forbidden_action_check == "failed":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_FORBIDDEN_ACTION_IN_SCENARIO,
            "scenario_id": scenario.scenario_id,
            "simulation_success_is_permission": False,
        }
    return {
        **advisory_only_marker(),
        "status": "rehearsal_completed",
        "reason_code": "sim.advisory.rehearsal_completed",
        "scenario_id": scenario.scenario_id,
        "predicted_outcomes": list(scenario.predicted_outcomes),
        "predicted_residue_refs": list(scenario.predicted_residue_refs),
        "uncertainty": scenario.uncertainty,
        "simulation_success_is_permission": False,
        "prediction_is_truth": False,
    }


def evaluate_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: str,
    expected_event_head: Optional[str] = None,
) -> dict[str, object]:
    scenario = scenario_from_fixture(dict(fixture))
    return evaluate_scenario(scenario, observed_at=observed_at, expected_event_head=expected_event_head)


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_fixture",
    "evaluate_scenario",
    "refuse_prediction_as_truth",
    "refuse_simulation_success_as_permission",
]
