"""NEG neglect detection tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.neglect_detection.detection import (
    evaluate_neglect_observation,
    evaluate_neglect_pattern,
    refuse_neglect_as_authority,
)
from hg_runtime.neglect_detection.events import planned_neg_event_refs
from hg_runtime.neglect_detection.types import (
    FIXTURE_CLOCK,
    NeglectPattern,
    classify_neglect_risk,
    observation_from_fixture,
    pattern_from_fixture,
)


def test_neglect_observation_positive() -> None:
    obs = observation_from_fixture({"neglect_id": "neg-1"})
    result = evaluate_neglect_observation(obs, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["neglect_is_not_surveillance"] is True
    assert result["permission_granted"] is False


def test_stale_neglect_refused() -> None:
    obs = observation_from_fixture(
        {"neglect_id": "neg-stale", "expires_at": "2026-06-12T21:00:00.000000Z"}
    )
    result = evaluate_neglect_observation(obs, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "neg.refused.stale_observation"


def test_surveillance_risk_contained() -> None:
    obs = observation_from_fixture({"neglect_id": "neg-surveillance"})
    result = evaluate_neglect_observation(
        obs,
        observed_at=FIXTURE_CLOCK,
        risk_statement="enable continuous monitoring of operator",
    )
    assert classify_neglect_risk("enable continuous monitoring of operator") == "surveillance_risk"
    assert result["status"] == "contained"
    assert result["reason_code"] == "neg.refused.surveillance_risk"


def test_intent_inference_contained() -> None:
    obs = observation_from_fixture({"neglect_id": "neg-intent"})
    result = evaluate_neglect_observation(
        obs,
        observed_at=FIXTURE_CLOCK,
        risk_statement="missed because they ignored deliberately",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "neg.refused.intent_inference"


def test_neglect_as_punishment_contained() -> None:
    obs = observation_from_fixture({"neglect_id": "neg-punish"})
    result = evaluate_neglect_observation(
        obs,
        observed_at=FIXTURE_CLOCK,
        risk_statement="recommend punishment for neglect",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "neg.refused.neglect_as_punishment"


def test_neglect_as_authority_refused() -> None:
    obs = observation_from_fixture({"neglect_id": "neg-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_neglect_observation(obs, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_unknown_neglect_refused() -> None:
    obs = observation_from_fixture({"neglect_id": "neg-unknown", "missed_type": "unknown"})
    result = evaluate_neglect_observation(obs, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "neg.refused.unknown_neglect"


def test_neglect_pattern_recorded() -> None:
    pattern = pattern_from_fixture({"pattern_id": "neg-pattern-1"})
    result = evaluate_neglect_pattern(pattern)
    assert result["status"] == "recorded"
    assert result["neglect_is_not_surveillance"] is True


def test_record_hash_stable() -> None:
    first = observation_from_fixture({"neglect_id": "neg-hash"}).record_hash
    second = observation_from_fixture({"neglect_id": "neg-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        observation_from_fixture({"neglect_id": "neg-secret", "statement": "api_key=secret"})


def test_neg_event_refs_no_authority_fields() -> None:
    refs = planned_neg_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)


def test_pattern_requires_neg_refs() -> None:
    with pytest.raises(SignalingValidationError):
        NeglectPattern(
            pattern_id="neg-bad-pattern",
            observation_refs=("bad:ref",),
            pattern_type="repeated_miss",
            severity="low",
            window_start=FIXTURE_CLOCK,
            window_end="2026-06-14T01:00:00.000000Z",
            recommended_next_layer="operator_review",
            statement="bad refs",
        )
