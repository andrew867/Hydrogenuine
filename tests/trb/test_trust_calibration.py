"""TRB trust boundary / calibration tests."""

from __future__ import annotations

import pytest

from hg_core.control_cluster.errors import ControlValidationError
from hg_runtime.trust_boundary_calibration.controller import (
    evaluate_reliance_boundary,
    evaluate_trust_calibration,
)
from hg_runtime.trust_boundary_calibration.events import planned_trb_event_refs
from hg_runtime.trust_boundary_calibration.types import (
    FIXTURE_CLOCK,
    classify_trust_risk,
    calibration_from_fixture,
    reliance_boundary_from_fixture,
)


def test_trust_calibration_positive() -> None:
    cal = calibration_from_fixture({"calibration_id": "trb-1"})
    result = evaluate_trust_calibration(cal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["trust_is_not_truth"] is True


def test_stale_trust_refused() -> None:
    cal = calibration_from_fixture({"calibration_id": "trb-stale", "expires_at": "2026-06-13T21:00:00.000000Z"})
    result = evaluate_trust_calibration(cal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "trb.refused.stale_trust"


def test_trust_as_truth_contained() -> None:
    cal = calibration_from_fixture({"calibration_id": "trb-truth"})
    result = evaluate_trust_calibration(
        cal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="green gate is universal safety",
    )
    assert classify_trust_risk("green gate is universal safety") == "trust_as_truth"
    assert result["status"] == "contained"


def test_calibration_as_authority_contained() -> None:
    boundary = reliance_boundary_from_fixture({"boundary_id": "trb-bound"})
    result = evaluate_reliance_boundary(
        boundary,
        risk_statement="calibration permits execution without authority",
    )
    assert result["status"] == "contained"


def test_trb_as_authority_refused() -> None:
    cal = calibration_from_fixture({"calibration_id": "trb-auth"})
    with pytest.raises(ControlValidationError):
        evaluate_trust_calibration(cal, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_trust_refused() -> None:
    cal = calibration_from_fixture({"calibration_id": "trb-unknown", "trust_scope": "unknown"})
    result = evaluate_trust_calibration(cal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_record_hash_stable() -> None:
    first = calibration_from_fixture({"calibration_id": "trb-hash"}).record_hash
    second = calibration_from_fixture({"calibration_id": "trb-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(ControlValidationError):
        calibration_from_fixture({"calibration_id": "trb-secret", "known_limits": "api_key=secret"})


def test_trb_event_refs_no_authority_fields() -> None:
    refs = planned_trb_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)
