"""SIM offline deterministic rehearsal tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.simulated_outcome_rehearsal.events import planned_rtc_events
from hg_runtime.simulated_outcome_rehearsal.rehearsal import (
    FIXTURE_CLOCK,
    evaluate_scenario,
    refuse_prediction_as_truth,
    refuse_simulation_success_as_permission,
)
from hg_runtime.simulated_outcome_rehearsal.types import SimulationScenario, scenario_from_fixture


def test_offline_rehearsal_positive() -> None:
    scenario = scenario_from_fixture({"scenario_id": "sim-1"})
    result = evaluate_scenario(scenario, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "rehearsal_completed"
    assert result["simulation_success_is_permission"] is False
    assert result["prediction_is_truth"] is False
    assert result["permission_granted"] is False


def test_expired_scenario_refused() -> None:
    scenario = scenario_from_fixture(
        {
            "scenario_id": "sim-exp",
            "expiry": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = evaluate_scenario(scenario, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sim.refused.expired_scenario"


def test_stale_scenario_refused() -> None:
    scenario = scenario_from_fixture(
        {
            "scenario_id": "sim-stale",
            "created_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_scenario(scenario, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sim.refused.stale_scenario"


def test_event_head_drift_refused() -> None:
    scenario = scenario_from_fixture({"scenario_id": "sim-drift"})
    result = evaluate_scenario(
        scenario,
        observed_at=FIXTURE_CLOCK,
        expected_event_head="sha256:other-head",
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "sim.refused.event_head_drift"


def test_forbidden_action_refused() -> None:
    scenario = scenario_from_fixture(
        {
            "scenario_id": "sim-forbidden",
            "forbidden_action_check": "failed",
        }
    )
    result = evaluate_scenario(scenario, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sim.refused.forbidden_action_in_scenario"


def test_live_planning_refused() -> None:
    scenario = scenario_from_fixture(
        {
            "scenario_id": "sim-live",
            "simulated_steps": "observe|live_model_call",
        }
    )
    with pytest.raises(RuntimeContextValidationError) as exc:
        evaluate_scenario(scenario, observed_at=FIXTURE_CLOCK)
    assert exc.value.code == "sim.refused.live_planning"


def test_simulation_not_permission_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_simulation_success_as_permission(treat_as_permit=True)


def test_prediction_not_truth_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_prediction_as_truth(treat_as_truth=True)


def test_record_hash_stable() -> None:
    a = scenario_from_fixture({"scenario_id": "stable"})
    b = scenario_from_fixture({"scenario_id": "stable"})
    assert a.record_hash == b.record_hash


def test_rtc_event_design_no_authority_fields() -> None:
    events = planned_rtc_events()
    assert len(events) >= 8
    assert all(not e.get("authority_fields") for e in events)


def test_schema_rejects_secret_world_state_hash() -> None:
    with pytest.raises(RuntimeContextValidationError):
        SimulationScenario(
            scenario_id="bad",
            proposal_ref="p",
            starting_event_head="sha256:head",
            starting_world_state_hash="password=secret",
            assumptions=(),
            simulated_steps=("observe",),
            predicted_outcomes=("advisory",),
            predicted_residue_refs=(),
            uncertainty="bounded",
            confidence="low",
            forbidden_action_check="passed",
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T20:00:00.000000Z",
        )
