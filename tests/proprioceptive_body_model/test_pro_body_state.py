"""PRO static body-state fixture tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.proprioceptive_body_model.backburner import (
    assert_pro_backburner_boundary,
    refuse_pro_off_backburner,
)
from hg_runtime.proprioceptive_body_model.events import planned_rtc_events
from hg_runtime.proprioceptive_body_model.types import BodyState, body_state_from_fixture
from hg_runtime.proprioceptive_body_model.validation import (
    FIXTURE_CLOCK,
    evaluate_body_state,
    refuse_contact_as_consent,
    refuse_reach_as_actuation,
    refuse_sensor_confidence_as_truth,
)


def test_static_body_state_positive() -> None:
    body_state = body_state_from_fixture({"body_state_id": "pro-1"})
    result = evaluate_body_state(body_state, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["reach_is_not_actuation_permission"] is True
    assert result["contact_is_not_consent"] is True
    assert result["sensor_confidence_is_not_truth"] is True
    assert result["permission_granted"] is False
    assert result["backburner_guard_active"] is True


def test_expired_body_state_refused() -> None:
    body_state = body_state_from_fixture(
        {
            "body_state_id": "pro-exp",
            "expiry": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = evaluate_body_state(body_state, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "pro.refused.expired_body_state"


def test_stale_body_state_refused() -> None:
    body_state = body_state_from_fixture(
        {
            "body_state_id": "pro-stale",
            "created_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_body_state(body_state, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "pro.refused.stale_body_state"


def test_event_head_drift_refused() -> None:
    body_state = body_state_from_fixture({"body_state_id": "pro-drift"})
    result = evaluate_body_state(
        body_state,
        observed_at=FIXTURE_CLOCK,
        expected_event_head="sha256:other-head",
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "pro.refused.event_head_drift"


def test_hardware_while_backburner_refused() -> None:
    body_state = body_state_from_fixture(
        {
            "body_state_id": "pro-hw",
            "platform_ref": "hardware:robot-arm",
            "actuator_refs": "actuator:gripper",
        }
    )
    with pytest.raises(RuntimeContextValidationError) as exc:
        evaluate_body_state(body_state, observed_at=FIXTURE_CLOCK)
    assert exc.value.code == "pro.refused.hardware_while_backburner"


def test_active_contact_high_confidence_review() -> None:
    body_state = body_state_from_fixture(
        {
            "body_state_id": "pro-contact",
            "contact_state": "active",
            "confidence": "high",
        }
    )
    result = evaluate_body_state(body_state, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "review"
    assert result["contact_is_not_consent"] is True


def test_reach_not_actuation_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_reach_as_actuation(treat_as_permit=True)


def test_contact_not_consent_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_contact_as_consent(treat_as_consent=True)


def test_sensor_confidence_not_truth_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_sensor_confidence_as_truth(treat_as_truth=True)


def test_backburner_boundary_asserted() -> None:
    boundary = assert_pro_backburner_boundary()
    assert boundary["backburner_guard_active"] is True
    assert boundary["runtime_disabled_by_default"] is True
    assert boundary["hardware_not_allowed_by_default"] is True
    assert boundary["planning_spec_declares_backburner"] is True
    assert boundary["embodiment_hardware_deferred"] is True


def test_runtime_activation_off_backburner_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_pro_off_backburner(allow_runtime=True)


def test_record_hash_stable() -> None:
    a = body_state_from_fixture({"body_state_id": "stable"})
    b = body_state_from_fixture({"body_state_id": "stable"})
    assert a.record_hash == b.record_hash


def test_rtc_event_design_no_authority_fields() -> None:
    events = planned_rtc_events()
    assert len(events) >= 9
    assert all(not e.get("authority_fields") for e in events)


def test_schema_rejects_secret_world_state_hash() -> None:
    with pytest.raises(RuntimeContextValidationError):
        BodyState(
            body_state_id="bad",
            platform_ref="fixture:static",
            sensor_refs=(),
            actuator_refs=(),
            pose_ref="pose:fixture",
            location_context="lab",
            reachable_zones=(),
            forbidden_zones=(),
            contact_state="none",
            motion_state="stationary",
            confidence="low",
            uncertainty="bounded",
            event_head="sha256:head",
            world_state_hash="password=secret",
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T20:00:00.000000Z",
        )
