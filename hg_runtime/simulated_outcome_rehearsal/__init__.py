"""SIM simulated outcome rehearsal — offline deterministic fixtures only."""

from hg_runtime.simulated_outcome_rehearsal.events import planned_rtc_events
from hg_runtime.simulated_outcome_rehearsal.rehearsal import (
    evaluate_fixture,
    evaluate_scenario,
    refuse_prediction_as_truth,
    refuse_simulation_success_as_permission,
)
from hg_runtime.simulated_outcome_rehearsal.types import (
    SIM_SCHEMA_VERSION,
    SimulationScenario,
    scenario_from_fixture,
)

__all__ = [
    "SIM_SCHEMA_VERSION",
    "SimulationScenario",
    "evaluate_fixture",
    "evaluate_scenario",
    "planned_rtc_events",
    "refuse_prediction_as_truth",
    "refuse_simulation_success_as_permission",
    "scenario_from_fixture",
]
