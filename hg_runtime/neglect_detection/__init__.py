"""NEG neglect detection — neglect is not surveillance."""

from hg_runtime.neglect_detection.detection import (
    evaluate_neglect_observation,
    evaluate_neglect_pattern,
    evaluate_observation_fixture,
    evaluate_pattern_fixture,
    refuse_neglect_as_authority,
)
from hg_runtime.neglect_detection.events import planned_neg_event_refs
from hg_runtime.neglect_detection.types import (
    FIXTURE_CLOCK,
    NeglectObservation,
    NeglectPattern,
    classify_neglect_risk,
    observation_from_fixture,
    pattern_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "NeglectObservation",
    "NeglectPattern",
    "classify_neglect_risk",
    "evaluate_neglect_observation",
    "evaluate_neglect_pattern",
    "evaluate_observation_fixture",
    "evaluate_pattern_fixture",
    "observation_from_fixture",
    "pattern_from_fixture",
    "planned_neg_event_refs",
    "refuse_neglect_as_authority",
]
