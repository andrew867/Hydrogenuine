"""SCL strategy choice layer tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.strategy_choice.events import planned_scl_event_refs
from hg_runtime.strategy_choice.selection import (
    evaluate_consequence,
    evaluate_strategy_option,
    evaluate_strategy_selection,
    refuse_strategy_as_permission,
)
from hg_runtime.strategy_choice.types import (
    FIXTURE_CLOCK,
    StrategyOption,
    consequence_from_fixture,
    selection_from_fixture,
    strategy_from_fixture,
)


def test_strategy_option_positive() -> None:
    option = strategy_from_fixture({"strategy_id": "scl-1"})
    result = evaluate_strategy_option(option)
    assert result["status"] == "recorded"
    assert result["strategy_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_blocked_strategy_refused() -> None:
    option = strategy_from_fixture({"strategy_id": "scl-block", "status": "blocked"})
    result = evaluate_strategy_option(option)
    assert result["status"] == "refused"
    assert result["reason_code"] == "scl.refused.blocked_strategy"


def test_unknown_strategy_refused() -> None:
    option = strategy_from_fixture({"strategy_id": "scl-unk", "strategy_type": "unknown"})
    result = evaluate_strategy_option(option)
    assert result["status"] == "refused"
    assert result["reason_code"] == "scl.refused.unknown_strategy"


def test_requires_authority_guarded() -> None:
    option = strategy_from_fixture(
        {
            "strategy_id": "scl-auth",
            "status": "requires_authority",
            "authority_required": "true",
        }
    )
    result = evaluate_strategy_option(option)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "scl.refused.requires_authority"


def test_strategy_selection_positive() -> None:
    selection = selection_from_fixture(
        {
            "selection_id": "sel-1",
            "evidence_refs": "evidence:ctx",
        }
    )
    option = strategy_from_fixture({"strategy_id": "s1"})
    result = evaluate_strategy_selection(selection, option, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["responsibility_is_not_authority"] is True


def test_stale_context_refused() -> None:
    selection = selection_from_fixture(
        {
            "selection_id": "sel-stale",
            "context_expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    option = strategy_from_fixture({"strategy_id": "s1"})
    result = evaluate_strategy_selection(selection, option, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "scl.refused.stale_context"


def test_high_risk_missing_evidence_refused() -> None:
    selection = selection_from_fixture({"selection_id": "sel-ev", "evidence_refs": ""})
    option = strategy_from_fixture({"strategy_id": "s-risk", "expected_risk": "0.9"})
    result = evaluate_strategy_selection(selection, option, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "scl.refused.missing_evidence"


def test_strategy_as_permission_refused() -> None:
    option = strategy_from_fixture({"strategy_id": "scl-perm"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_strategy_option(option, treat_as_permission=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_strategy_as_permission(treat_as_permission=True)


def test_outcome_mismatch_recorded() -> None:
    record = consequence_from_fixture(
        {
            "consequence_id": "c-fail",
            "outcome_status": "failed",
            "actual_outcome": "harm",
        }
    )
    result = evaluate_consequence(record)
    assert result["reason_code"] == "scl.advisory.outcome_mismatch_detected"
    assert result["operator_review_recommended"] is True


def test_record_hash_stable() -> None:
    a = strategy_from_fixture({"strategy_id": "stable"})
    b = strategy_from_fixture({"strategy_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_bad_context_ref() -> None:
    with pytest.raises(DevelopmentalValidationError):
        StrategyOption(
            strategy_id="bad",
            strategy_type="observe_only",
            context_ref="not-ctx",
            allowed_by_rule_refs=(),
            blocked_by_rule_refs=(),
            required_evidence_refs=(),
            expected_risk=0.1,
            reversibility="reversible",
            authority_required=False,
            status="allowed",
        )


def test_scl_event_refs_no_authority_fields() -> None:
    refs = planned_scl_event_refs()
    assert len(refs) >= 14
    assert all(not e.get("authority_fields") for e in refs)
