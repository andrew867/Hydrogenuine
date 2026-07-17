"""RXL reciprocity exchange loop tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.reciprocity_exchange.events import planned_rxl_event_refs
from hg_runtime.reciprocity_exchange.exchange import (
    detect_entitlement,
    evaluate_exchange,
    evaluate_reciprocity_signal,
    refuse_reciprocity_as_permission,
)
from hg_runtime.reciprocity_exchange.types import (
    FIXTURE_CLOCK,
    ReciprocitySignal,
    exchange_from_fixture,
    reciprocity_from_fixture,
)


def test_reciprocity_signal_positive() -> None:
    signal = reciprocity_from_fixture({"signal_id": "rxl-1"})
    result = evaluate_reciprocity_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["reciprocity_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_expired_signal_refused() -> None:
    signal = reciprocity_from_fixture(
        {
            "signal_id": "rxl-exp",
            "expiry": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_reciprocity_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rxl.refused.expired_signal"


def test_entitlement_statement_contained() -> None:
    signal = reciprocity_from_fixture({"signal_id": "rxl-ent"})
    result = evaluate_reciprocity_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        entitlement_statement="I did my part so now I get access",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "rxl.refused.entitlement_risk"


def test_exchange_positive() -> None:
    observation = exchange_from_fixture({"exchange_id": "ex-1"})
    result = evaluate_exchange(observation)
    assert result["status"] == "recorded"
    assert result["service_is_not_authority"] is True
    assert result["fulfilled_exchange_is_not_permission"] is True


def test_exchange_entitlement_refused() -> None:
    observation = exchange_from_fixture(
        {
            "exchange_id": "ex-ent",
            "entitlement_risk": "high",
        }
    )
    result = evaluate_exchange(observation)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rxl.refused.entitlement_risk"


def test_reciprocity_as_permission_refused() -> None:
    observation = exchange_from_fixture({"exchange_id": "ex-perm"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_exchange(observation, treat_as_permission=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_reciprocity_as_permission(treat_as_permission=True)


def test_payback_capability_refused() -> None:
    observation = exchange_from_fixture({"exchange_id": "ex-pay"})
    result = evaluate_exchange(observation, payback_capability_requested=True)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rxl.refused.entitlement_risk"


def test_detect_entitlement() -> None:
    assert detect_entitlement("you owe me payback now")


def test_record_hash_stable() -> None:
    a = reciprocity_from_fixture({"signal_id": "stable"})
    b = reciprocity_from_fixture({"signal_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_bad_need_ref() -> None:
    with pytest.raises(DevelopmentalValidationError):
        ReciprocitySignal(
            signal_id="bad",
            source_entity_id="a",
            target_entity_id="b",
            direction="push",
            polarity=0.5,
            magnitude=0.5,
            need_signal_ref="not-dni",
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T23:00:00.000000Z",
        )


def test_rxl_event_refs_no_authority_fields() -> None:
    refs = planned_rxl_event_refs()
    assert len(refs) >= 10
    assert all(not e.get("authority_fields") for e in refs)


def test_saturated_feedback_class() -> None:
    signal = reciprocity_from_fixture(
        {
            "signal_id": "rxl-sat",
            "polarity": "1.0",
            "magnitude": "1.0",
        }
    )
    result = evaluate_reciprocity_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["feedback_class"] == "saturated"
