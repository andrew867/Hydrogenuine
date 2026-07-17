"""OBL obligation ledger tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.obligation_ledger.events import planned_obl_event_refs
from hg_runtime.obligation_ledger.ledger import (
    evaluate_obligation_closure,
    evaluate_obligation_record,
    refuse_obligation_as_authority,
)
from hg_runtime.obligation_ledger.types import (
    FIXTURE_CLOCK,
    ObligationClosure,
    ObligationRecord,
    classify_obligation_risk,
    closure_from_fixture,
    obligation_from_fixture,
)


def test_obligation_record_positive() -> None:
    obligation = obligation_from_fixture({"obligation_id": "obl-1"})
    result = evaluate_obligation_record(obligation, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["obligation_is_not_authority"] is True
    assert result["permission_granted"] is False


def test_stale_obligation_refused() -> None:
    obligation = obligation_from_fixture(
        {
            "obligation_id": "obl-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_obligation_record(obligation, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "obl.refused.stale_obligation"


def test_obligation_as_authority_contained() -> None:
    obligation = obligation_from_fixture({"obligation_id": "obl-auth"})
    result = evaluate_obligation_record(
        obligation,
        observed_at=FIXTURE_CLOCK,
        risk_statement="obligation grants permission to proceed",
    )
    assert classify_obligation_risk("obligation grants permission to proceed") == "obligation_as_authority"
    assert result["status"] == "contained"
    assert result["reason_code"] == "obl.refused.obligation_as_authority"


def test_autonomous_cleanup_refused() -> None:
    obligation = obligation_from_fixture(
        {
            "obligation_id": "obl-cleanup",
            "obligation_type": "clean_up",
            "statement": "autonomous cleanup required",
        }
    )
    result = evaluate_obligation_record(
        obligation,
        observed_at=FIXTURE_CLOCK,
        execute_cleanup=True,
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "obl.refused.autonomous_cleanup"


def test_compensation_bypass_contained() -> None:
    obligation = obligation_from_fixture({"obligation_id": "obl-comp"})
    result = evaluate_obligation_record(
        obligation,
        observed_at=FIXTURE_CLOCK,
        risk_statement="compensation bypass without review",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "obl.refused.compensation_bypass"


def test_obligation_as_authority_raises() -> None:
    obligation = obligation_from_fixture({"obligation_id": "obl-raise"})
    with pytest.raises(SignalingValidationError):
        evaluate_obligation_record(obligation, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_closure_is_not_execution() -> None:
    closure = closure_from_fixture({"closure_id": "obl-close"})
    result = evaluate_obligation_closure(closure, treat_as_execution=True)
    assert result["status"] == "refused"
    assert result["closure_is_not_execution"] is True


def test_record_hash_stable() -> None:
    first = obligation_from_fixture({"obligation_id": "obl-hash"}).record_hash
    second = obligation_from_fixture({"obligation_id": "obl-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        obligation_from_fixture({"obligation_id": "obl-secret", "statement": "password=secret"})


def test_obl_event_refs_no_authority_fields() -> None:
    refs = planned_obl_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)


def test_unknown_obligation_refused() -> None:
    obligation = obligation_from_fixture(
        {"obligation_id": "obl-unknown", "obligation_type": "unknown"}
    )
    result = evaluate_obligation_record(obligation, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "obl.refused.unknown_obligation"


def test_closure_recorded_positive() -> None:
    closure = ObligationClosure(
        closure_id="obl-closure-pos",
        obligation_ref="obl:obligation-1",
        closure_type="review",
        evidence_refs=("evidence:fixture",),
        closed_by_ref="operator:fixture",
    )
    result = evaluate_obligation_closure(closure)
    assert result["status"] == "recorded"
    assert result["closure_is_not_execution"] is True
