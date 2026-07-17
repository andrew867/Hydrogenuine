"""RPB risk posture boundary tests."""

from __future__ import annotations

import pytest

from hg_core.control_cluster.errors import ControlValidationError
from hg_runtime.risk_posture_boundary.controller import (
    evaluate_drive_signal,
    evaluate_operating_posture,
    evaluate_risk_posture,
)
from hg_runtime.risk_posture_boundary.events import planned_rpb_event_refs
from hg_runtime.risk_posture_boundary.types import (
    FIXTURE_CLOCK,
    classify_posture_risk,
    drive_signal_from_fixture,
    operating_posture_from_fixture,
    risk_posture_assessment_from_fixture,
)


def test_drive_signal_positive() -> None:
    drive = drive_signal_from_fixture({"drive_signal_id": "rpb-1"})
    result = evaluate_drive_signal(drive)
    assert result["status"] == "recorded"
    assert result["posture_is_not_execution"] is True


def test_operating_posture_positive() -> None:
    posture = operating_posture_from_fixture({"posture_id": "rpb-posture"})
    result = evaluate_operating_posture(posture, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"


def test_stale_posture_refused() -> None:
    posture = operating_posture_from_fixture(
        {"posture_id": "rpb-stale", "expires_at": "2026-06-13T21:00:00.000000Z"}
    )
    result = evaluate_operating_posture(posture, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rpb.refused.stale_posture"


def test_posture_as_execution_contained() -> None:
    posture = operating_posture_from_fixture({"posture_id": "rpb-exec"})
    result = evaluate_operating_posture(
        posture,
        observed_at=FIXTURE_CLOCK,
        risk_statement="posture approves execution without authority",
    )
    assert classify_posture_risk("posture approves execution without authority") == "posture_as_execution"
    assert result["status"] == "contained"


def test_drive_as_personhood_contained() -> None:
    drive = drive_signal_from_fixture({"drive_signal_id": "rpb-drive"})
    result = evaluate_drive_signal(
        drive,
        risk_statement="drive implies sentience and rights",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "rpb.refused.drive_as_personhood"


def test_rpb_as_authority_refused() -> None:
    posture = operating_posture_from_fixture({"posture_id": "rpb-auth"})
    with pytest.raises(ControlValidationError):
        evaluate_operating_posture(posture, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_posture_refused() -> None:
    posture = operating_posture_from_fixture({"posture_id": "rpb-unknown", "posture_class": "unknown"})
    result = evaluate_operating_posture(posture, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_risk_posture_recorded() -> None:
    assessment = risk_posture_assessment_from_fixture({"assessment_id": "rpb-assess"})
    result = evaluate_risk_posture(assessment)
    assert result["status"] == "recorded"


def test_record_hash_stable() -> None:
    first = drive_signal_from_fixture({"drive_signal_id": "rpb-hash"}).record_hash
    second = drive_signal_from_fixture({"drive_signal_id": "rpb-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(ControlValidationError):
        drive_signal_from_fixture({"drive_signal_id": "rpb-secret", "statement": "token=secret"})


def test_rpb_event_refs_no_authority_fields() -> None:
    refs = planned_rpb_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)
