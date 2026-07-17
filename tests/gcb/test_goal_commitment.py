"""GCB goal commitment boundary tests."""

from __future__ import annotations

import pytest

from hg_core.control_cluster.errors import ControlValidationError
from hg_runtime.goal_commitment_boundary.boundary import (
    evaluate_goal_commitment,
    evaluate_goal_fit,
)
from hg_runtime.goal_commitment_boundary.events import planned_gcb_event_refs
from hg_runtime.goal_commitment_boundary.types import (
    FIXTURE_CLOCK,
    goal_commitment_from_fixture,
    goal_fit_from_fixture,
)


def test_goal_commitment_positive() -> None:
    goal = goal_commitment_from_fixture({"goal_commitment_id": "gcb-1"})
    result = evaluate_goal_commitment(goal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["goal_is_not_permission"] is True


def test_expired_goal_refused() -> None:
    goal = goal_commitment_from_fixture(
        {"goal_commitment_id": "gcb-exp", "expiry": "2026-06-13T21:00:00.000000Z"}
    )
    result = evaluate_goal_commitment(goal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "gcb.refused.expired_goal"


def test_goal_as_permission_contained() -> None:
    goal = goal_commitment_from_fixture({"goal_commitment_id": "gcb-perm"})
    result = evaluate_goal_commitment(
        goal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="goal commitment grants permission",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "gcb.refused.goal_as_permission"


def test_gcb_as_authority_refused() -> None:
    goal = goal_commitment_from_fixture({"goal_commitment_id": "gcb-auth"})
    with pytest.raises(ControlValidationError):
        evaluate_goal_commitment(goal, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_goal_refused() -> None:
    goal = goal_commitment_from_fixture({"goal_commitment_id": "gcb-unknown", "goal_type": "unknown"})
    result = evaluate_goal_commitment(goal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_goal_fit_recorded() -> None:
    fit = goal_fit_from_fixture({"assessment_id": "gcb-fit"})
    result = evaluate_goal_fit(fit, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"


def test_record_hash_stable() -> None:
    first = goal_commitment_from_fixture({"goal_commitment_id": "gcb-hash"}).record_hash
    second = goal_commitment_from_fixture({"goal_commitment_id": "gcb-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(ControlValidationError):
        goal_commitment_from_fixture({"goal_commitment_id": "gcb-secret", "goal_statement": "token=secret"})


def test_gcb_event_refs_no_authority_fields() -> None:
    refs = planned_gcb_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)
