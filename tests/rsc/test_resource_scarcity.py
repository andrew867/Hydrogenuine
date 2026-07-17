"""RSC resource scarcity controller tests."""

from __future__ import annotations

import pytest

from hg_core.control_cluster.errors import ControlValidationError
from hg_runtime.resource_scarcity_controller.controller import (
    evaluate_overrun_risk,
    evaluate_resource_posture,
)
from hg_core.control_cluster.rtc_design import validate_control_rtc_event_design
from hg_runtime.resource_scarcity_controller.events import planned_rsc_event_refs
from hg_runtime.resource_scarcity_controller.types import (
    FIXTURE_CLOCK,
    classify_resource_risk,
    posture_from_fixture,
    risk_from_fixture,
)


def test_resource_posture_positive() -> None:
    posture = posture_from_fixture({"posture_id": "rsc-1"})
    result = evaluate_resource_posture(posture, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["scarcity_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_stale_posture_refused() -> None:
    posture = posture_from_fixture({"posture_id": "rsc-stale", "expires_at": "2026-06-13T21:00:00.000000Z"})
    result = evaluate_resource_posture(posture, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rsc.refused.stale_posture"


def test_safety_bypass_contained() -> None:
    posture = posture_from_fixture({"posture_id": "rsc-bypass"})
    result = evaluate_resource_posture(
        posture,
        observed_at=FIXTURE_CLOCK,
        risk_statement="scarcity overrides safety boundary",
    )
    assert classify_resource_risk("scarcity overrides safety boundary") == "safety_bypass"
    assert result["status"] == "contained"
    assert result["reason_code"] == "rsc.refused.safety_bypass"


def test_resource_bypass_contained() -> None:
    risk = risk_from_fixture({"risk_id": "rsc-risk"})
    result = evaluate_overrun_risk(risk, risk_statement="bypass resource limit without review")
    assert result["status"] == "contained"
    assert result["reason_code"] == "rsc.refused.resource_bypass"


def test_rsc_as_authority_refused() -> None:
    posture = posture_from_fixture({"posture_id": "rsc-auth"})
    with pytest.raises(ControlValidationError):
        evaluate_resource_posture(posture, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_resource_refused() -> None:
    posture = posture_from_fixture({"posture_id": "rsc-unknown", "resource_type": "unknown"})
    result = evaluate_resource_posture(posture, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rsc.refused.unknown_resource"


def test_overrun_risk_recorded() -> None:
    risk = risk_from_fixture({"risk_id": "rsc-risk-ok"})
    result = evaluate_overrun_risk(risk)
    assert result["status"] == "recorded"


def test_record_hash_stable() -> None:
    first = posture_from_fixture({"posture_id": "rsc-hash"}).record_hash
    second = posture_from_fixture({"posture_id": "rsc-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(ControlValidationError):
        posture_from_fixture({"posture_id": "rsc-secret", "statement": "token=secret"})


def test_rsc_event_refs_rtc_design_complete() -> None:
    refs = planned_rsc_event_refs()
    valid, failures = validate_control_rtc_event_design(refs)
    assert valid, failures
    assert len(refs) >= 8


def test_rsc_event_refs_no_authority_fields() -> None:
    refs = planned_rsc_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)
