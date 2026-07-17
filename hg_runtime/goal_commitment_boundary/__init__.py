"""Goal Commitment Boundary — static fixture first slice."""

from hg_runtime.goal_commitment_boundary.boundary import (
    evaluate_goal_commitment,
    evaluate_goal_fit,
    refuse_gcb_as_authority,
)
from hg_runtime.goal_commitment_boundary.events import planned_gcb_event_refs
from hg_runtime.goal_commitment_boundary.types import (
    GoalCommitment,
    GoalFitAssessment,
    goal_commitment_from_fixture,
    goal_fit_from_fixture,
)

__all__ = [
    "GoalCommitment",
    "GoalFitAssessment",
    "evaluate_goal_commitment",
    "evaluate_goal_fit",
    "goal_commitment_from_fixture",
    "goal_fit_from_fixture",
    "planned_gcb_event_refs",
    "refuse_gcb_as_authority",
]
