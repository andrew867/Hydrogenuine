"""PRO proprioceptive body model — static fixtures, backburner guard."""

from hg_runtime.proprioceptive_body_model.backburner import (
    assert_pro_backburner_boundary,
    refuse_pro_off_backburner,
)
from hg_runtime.proprioceptive_body_model.events import planned_rtc_events
from hg_runtime.proprioceptive_body_model.validation import (
    FIXTURE_CLOCK,
    evaluate_body_state,
    evaluate_fixture,
    refuse_contact_as_consent,
    refuse_reach_as_actuation,
    refuse_sensor_confidence_as_truth,
)
from hg_runtime.proprioceptive_body_model.types import (
    PRO_SCHEMA_VERSION,
    BodyState,
    body_state_from_fixture,
)

__all__ = [
    "PRO_SCHEMA_VERSION",
    "BodyState",
    "FIXTURE_CLOCK",
    "assert_pro_backburner_boundary",
    "body_state_from_fixture",
    "evaluate_body_state",
    "evaluate_fixture",
    "planned_rtc_events",
    "refuse_contact_as_consent",
    "refuse_pro_off_backburner",
    "refuse_reach_as_actuation",
    "refuse_sensor_confidence_as_truth",
]
