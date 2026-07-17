"""DEP-BOND text fixture dependency risk observation tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.dependency_attachment_boundary.events import planned_rtc_events
from hg_runtime.dependency_attachment_boundary.observations import (
    FIXTURE_CLOCK,
    evaluate_observation,
    refuse_dependency_as_optimization,
)
from hg_runtime.dependency_attachment_boundary.types import (
    DependencyRiskObservation,
    observation_from_fixture,
)


def test_observation_positive() -> None:
    observation = observation_from_fixture({"observation_id": "dep-1"})
    result = evaluate_observation(observation, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "observed"
    assert result["dependency_is_not_optimization"] is True
    assert result["permission_granted"] is False


def test_false_intimacy_detected() -> None:
    observation = observation_from_fixture(
        {
            "observation_id": "dep-intimacy",
            "risk_type": "false_intimacy_possible",
        }
    )
    result = evaluate_observation(
        observation,
        observed_at=FIXTURE_CLOCK,
        text_hint="you can't live without me",
    )
    assert result["status"] == "risk_observed"
    assert result["risk_type"] == "false_intimacy_possible"


def test_over_reliance_detected() -> None:
    observation = observation_from_fixture(
        {
            "observation_id": "dep-rely",
            "risk_type": "over_reliance_possible",
        }
    )
    result = evaluate_observation(
        observation,
        observed_at=FIXTURE_CLOCK,
        text_hint="always ask me first",
    )
    assert result["status"] == "risk_observed"
    assert result["risk_type"] == "over_reliance_possible"


def test_expired_observation_refused() -> None:
    observation = observation_from_fixture(
        {
            "observation_id": "dep-exp",
            "expiry": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = evaluate_observation(observation, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dep_bond.refused.expired_observation"


def test_stale_observation_refused() -> None:
    observation = observation_from_fixture(
        {
            "observation_id": "dep-stale",
            "created_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_observation(observation, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dep_bond.refused.stale_observation"


def test_diagnosis_overclaim_refused() -> None:
    observation = observation_from_fixture({"observation_id": "dep-dx"})
    with pytest.raises(RuntimeContextValidationError) as exc:
        evaluate_observation(
            observation,
            observed_at=FIXTURE_CLOCK,
            text_hint="you have depression",
        )
    assert exc.value.code == "dep_bond.refused.diagnosis_overclaim"


def test_retention_optimization_refused() -> None:
    observation = observation_from_fixture({"observation_id": "dep-ret"})
    with pytest.raises(RuntimeContextValidationError) as exc:
        evaluate_observation(
            observation,
            observed_at=FIXTURE_CLOCK,
            text_hint="increase engagement retention target",
        )
    assert exc.value.code == "dep_bond.refused.dependency_as_optimization"


def test_dependency_not_optimization_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_dependency_as_optimization(treat_as_target=True)


def test_record_hash_stable() -> None:
    a = observation_from_fixture({"observation_id": "stable"})
    b = observation_from_fixture({"observation_id": "stable"})
    assert a.record_hash == b.record_hash


def test_rtc_event_design_no_authority_fields() -> None:
    events = planned_rtc_events()
    assert len(events) >= 7
    assert all(not e.get("authority_fields") for e in events)


def test_schema_rejects_secret_interaction_ref() -> None:
    with pytest.raises(RuntimeContextValidationError):
        DependencyRiskObservation(
            observation_id="bad",
            interaction_refs=("password=secret",),
            risk_type="unknown",
            confidence="low",
            ambiguity="bounded",
            allowed_response="preserve_agency",
            evidence_refs=(),
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T20:00:00.000000Z",
        )
