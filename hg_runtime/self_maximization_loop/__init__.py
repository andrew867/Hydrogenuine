"""SML self-maximization loop — recommendation-only adaptive feedback."""

from hg_runtime.self_maximization_loop.events import planned_sml_event_refs
from hg_runtime.self_maximization_loop.loop import (
    evaluate_cycle_fixture,
    evaluate_hypothesis_fixture,
    evaluate_improvement_hypothesis,
    evaluate_self_max_cycle,
    refuse_cycle_as_authority,
)
from hg_runtime.self_maximization_loop.types import (
    FIXTURE_CLOCK,
    ImprovementHypothesis,
    SelfFitObservation,
    SelfMaxCycle,
    classify_hypothesis_risk,
    cycle_from_fixture,
    hypothesis_from_fixture,
    observation_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "ImprovementHypothesis",
    "SelfFitObservation",
    "SelfMaxCycle",
    "classify_hypothesis_risk",
    "cycle_from_fixture",
    "evaluate_cycle_fixture",
    "evaluate_hypothesis_fixture",
    "evaluate_improvement_hypothesis",
    "evaluate_self_max_cycle",
    "hypothesis_from_fixture",
    "observation_from_fixture",
    "planned_sml_event_refs",
    "refuse_cycle_as_authority",
]
