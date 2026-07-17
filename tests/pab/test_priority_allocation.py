"""PAB priority allocation boundary tests."""

from __future__ import annotations

import pytest

from hg_core.control_cluster.errors import ControlValidationError
from hg_runtime.priority_allocation_boundary.boundary import (
    evaluate_priority_assessment,
    evaluate_priority_signal,
)
from hg_runtime.priority_allocation_boundary.events import planned_pab_event_refs
from hg_runtime.priority_allocation_boundary.types import (
    FIXTURE_CLOCK,
    priority_assessment_from_fixture,
    priority_signal_from_fixture,
)


def test_priority_signal_positive() -> None:
    signal = priority_signal_from_fixture({"priority_signal_id": "pab-1"})
    result = evaluate_priority_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["priority_is_not_permission"] is True


def test_stale_priority_refused() -> None:
    signal = priority_signal_from_fixture(
        {"priority_signal_id": "pab-stale", "expires_at": "2026-06-13T21:00:00.000000Z"}
    )
    result = evaluate_priority_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "pab.refused.stale_priority"


def test_priority_as_permission_contained() -> None:
    signal = priority_signal_from_fixture({"priority_signal_id": "pab-perm"})
    result = evaluate_priority_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="high priority grants permission to execute",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "pab.refused.priority_as_permission"


def test_priority_as_authority_refused() -> None:
    signal = priority_signal_from_fixture({"priority_signal_id": "pab-auth"})
    with pytest.raises(ControlValidationError):
        evaluate_priority_signal(signal, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_priority_refused() -> None:
    signal = priority_signal_from_fixture({"priority_signal_id": "pab-unknown", "signal_type": "unknown"})
    result = evaluate_priority_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_priority_assessment_recorded() -> None:
    assessment = priority_assessment_from_fixture({"assessment_id": "pab-assess"})
    result = evaluate_priority_assessment(assessment)
    assert result["status"] == "recorded"


def test_record_hash_stable() -> None:
    first = priority_signal_from_fixture({"priority_signal_id": "pab-hash"}).record_hash
    second = priority_signal_from_fixture({"priority_signal_id": "pab-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(ControlValidationError):
        priority_signal_from_fixture({"priority_signal_id": "pab-secret", "statement": "api_key=secret"})


def test_pab_event_refs_no_authority_fields() -> None:
    refs = planned_pab_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)
