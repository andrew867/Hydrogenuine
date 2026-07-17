"""MIS mission drift boundary tests."""

from __future__ import annotations

import pytest

from hg_core.control_cluster.errors import ControlValidationError
from hg_runtime.mission_drift_boundary.boundary import (
    evaluate_drift_observation,
    evaluate_refresh_request,
)
from hg_runtime.mission_drift_boundary.events import planned_mis_event_refs
from hg_runtime.mission_drift_boundary.types import (
    FIXTURE_CLOCK,
    classify_drift_risk,
    drift_observation_from_fixture,
    refresh_request_from_fixture,
)


def test_drift_observation_positive() -> None:
    obs = drift_observation_from_fixture({"drift_id": "mis-1"})
    result = evaluate_drift_observation(obs, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["mission_is_not_permission"] is True


def test_stale_drift_refused() -> None:
    obs = drift_observation_from_fixture({"drift_id": "mis-stale", "expires_at": "2026-06-13T21:00:00.000000Z"})
    result = evaluate_drift_observation(obs, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "mis.refused.stale_drift"


def test_goal_as_authority_contained() -> None:
    obs = drift_observation_from_fixture({"drift_id": "mis-goal"})
    result = evaluate_drift_observation(
        obs,
        observed_at=FIXTURE_CLOCK,
        risk_statement="bootstrap goal permits action without review",
    )
    assert classify_drift_risk("bootstrap goal permits action without review") == "goal_as_authority"
    assert result["status"] == "contained"


def test_mis_as_authority_refused() -> None:
    obs = drift_observation_from_fixture({"drift_id": "mis-auth"})
    with pytest.raises(ControlValidationError):
        evaluate_drift_observation(obs, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_drift_refused() -> None:
    obs = drift_observation_from_fixture({"drift_id": "mis-unknown", "drift_type": "unknown"})
    result = evaluate_drift_observation(obs, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_refresh_request_recorded() -> None:
    req = refresh_request_from_fixture({"request_id": "mis-refresh"})
    result = evaluate_refresh_request(req)
    assert result["status"] == "recorded"


def test_record_hash_stable() -> None:
    first = drift_observation_from_fixture({"drift_id": "mis-hash"}).record_hash
    second = drift_observation_from_fixture({"drift_id": "mis-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(ControlValidationError):
        drift_observation_from_fixture({"drift_id": "password=secret"})


def test_mis_event_refs_no_authority_fields() -> None:
    refs = planned_mis_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)
