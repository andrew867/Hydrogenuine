"""SAB self-awareness boundary package."""

from hg_runtime.self_awareness_boundary.boundary import (
    evaluate_overreach_fixture,
    evaluate_self_model,
    evaluate_self_model_fixture,
    evaluate_self_overreach,
    refuse_self_model_as_authority,
)
from hg_runtime.self_awareness_boundary.events import planned_sab_event_refs
from hg_runtime.self_awareness_boundary.types import (
    FIXTURE_CLOCK,
    SelfModel,
    SelfOverreachSignal,
    classify_overreach,
    overreach_from_fixture,
    self_model_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "SelfModel",
    "SelfOverreachSignal",
    "classify_overreach",
    "evaluate_overreach_fixture",
    "evaluate_self_model",
    "evaluate_self_model_fixture",
    "evaluate_self_overreach",
    "overreach_from_fixture",
    "planned_sab_event_refs",
    "refuse_self_model_as_authority",
    "self_model_from_fixture",
]
