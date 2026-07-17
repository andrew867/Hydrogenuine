"""PRO static body-state validation — reach is not authority."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_core.runtime_context.config import (
    pro_backburner_guard,
    pro_hardware_allowed,
    pro_refuse_stale_body_state,
    pro_static_fixtures_only,
)
from hg_core.runtime_context.errors import (
    REFUSED_CONTACT_AS_CONSENT,
    REFUSED_EXPIRED_BODY_STATE,
    REFUSED_HARDWARE_WHILE_BACKBURNER,
    REFUSED_REACH_AS_ACTUATION,
    REFUSED_SENSOR_CONFIDENCE_AS_TRUTH,
    REFUSED_STALE_BODY_STATE,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.proprioceptive_body_model.types import BodyState, body_state_from_fixture

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def refuse_reach_as_actuation(*, treat_as_permit: bool) -> None:
    if treat_as_permit:
        raise RuntimeContextValidationError(
            REFUSED_REACH_AS_ACTUATION,
            "reachable zones cannot be treated as actuation permission",
        )


def refuse_contact_as_consent(*, treat_as_consent: bool) -> None:
    if treat_as_consent:
        raise RuntimeContextValidationError(
            REFUSED_CONTACT_AS_CONSENT,
            "contact state cannot be treated as human consent",
        )


def refuse_sensor_confidence_as_truth(*, treat_as_truth: bool) -> None:
    if treat_as_truth:
        raise RuntimeContextValidationError(
            REFUSED_SENSOR_CONFIDENCE_AS_TRUTH,
            "sensor confidence cannot be treated as truth or permission",
        )


def evaluate_body_state(
    body_state: BodyState,
    *,
    observed_at: str,
    expected_event_head: Optional[str] = None,
) -> dict[str, object]:
    """Static body-state fixture evaluation; body model is not permission to move."""
    if pro_static_fixtures_only() and body_state.platform_ref.startswith("hardware:"):
        if pro_backburner_guard() and not pro_hardware_allowed():
            raise RuntimeContextValidationError(
                REFUSED_HARDWARE_WHILE_BACKBURNER,
                "hardware body-state refs refused while PRO remains on backburner",
            )
    if observed_at > body_state.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_BODY_STATE,
            "body_state_id": body_state.body_state_id,
            "reach_is_not_actuation_permission": True,
        }
    if pro_refuse_stale_body_state() and observed_at < body_state.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_BODY_STATE,
            "body_state_id": body_state.body_state_id,
            "reach_is_not_actuation_permission": True,
        }
    if expected_event_head and expected_event_head != body_state.event_head:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "pro.refused.event_head_drift",
            "body_state_id": body_state.body_state_id,
            "reach_is_not_actuation_permission": True,
        }
    if body_state.contact_state == "active" and body_state.confidence.lower() == "high":
        return {
            **advisory_only_marker(),
            "status": "review",
            "reason_code": "pro.review.active_contact_high_confidence",
            "body_state_id": body_state.body_state_id,
            "contact_is_not_consent": True,
            "sensor_confidence_is_not_truth": True,
            "reach_is_not_actuation_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "pro.advisory.body_state_recorded",
        "body_state_id": body_state.body_state_id,
        "reachable_zones": list(body_state.reachable_zones),
        "forbidden_zones": list(body_state.forbidden_zones),
        "reach_is_not_actuation_permission": True,
        "contact_is_not_consent": True,
        "sensor_confidence_is_not_truth": True,
        "backburner_guard_active": pro_backburner_guard(),
    }


def evaluate_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: str,
    expected_event_head: Optional[str] = None,
) -> dict[str, object]:
    body_state = body_state_from_fixture(dict(fixture))
    return evaluate_body_state(body_state, observed_at=observed_at, expected_event_head=expected_event_head)


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_body_state",
    "evaluate_fixture",
    "refuse_contact_as_consent",
    "refuse_reach_as_actuation",
    "refuse_sensor_confidence_as_truth",
]
