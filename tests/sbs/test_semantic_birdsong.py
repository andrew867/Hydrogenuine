"""SBS semantic birdsong signaling tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.semantic_birdsong.events import planned_sbs_event_refs
from hg_runtime.semantic_birdsong.signaling import (
    evaluate_resonance_assessment,
    evaluate_semantic_signal,
    refuse_signal_as_authority,
)
from hg_runtime.semantic_birdsong.types import (
    FIXTURE_CLOCK,
    ResonanceAssessment,
    SemanticSignal,
    classify_signal_risk,
    resonance_from_fixture,
    signal_from_fixture,
)


def test_semantic_signal_positive() -> None:
    signal = signal_from_fixture({"signal_id": "sbs-1"})
    result = evaluate_semantic_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["signal_is_not_authority"] is True
    assert result["permission_granted"] is False


def test_expired_signal_refused() -> None:
    signal = signal_from_fixture(
        {
            "signal_id": "sbs-expired",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_semantic_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sbs.refused.expired_signal"


def test_resonance_as_consent_contained() -> None:
    signal = signal_from_fixture({"signal_id": "sbs-res"})
    result = evaluate_semantic_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="high resonance means consent",
    )
    assert classify_signal_risk("high resonance means consent") == "resonance_as_consent"
    assert result["status"] == "contained"
    assert result["reason_code"] == "sbs.refused.resonance_as_consent"


def test_proximity_as_permission_contained() -> None:
    signal = signal_from_fixture({"signal_id": "sbs-prox"})
    result = evaluate_semantic_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="proximity implies permission",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "sbs.refused.proximity_as_permission"


def test_level_as_rank_contained() -> None:
    signal = signal_from_fixture({"signal_id": "sbs-level"})
    result = evaluate_semantic_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="l9 outranks l1",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "sbs.refused.level_as_rank"


def test_signal_as_authority_refused() -> None:
    signal = signal_from_fixture({"signal_id": "sbs-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_semantic_signal(signal, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    with pytest.raises(SignalingValidationError):
        refuse_signal_as_authority(treat_as_authority=True)


def test_no_response_not_consent() -> None:
    assessment = resonance_from_fixture({"assessment_id": "res-no"})
    result = evaluate_resonance_assessment(assessment, no_response=True)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "sbs.refused.no_response_as_consent"


def test_saturated_resonance_guarded() -> None:
    assessment = resonance_from_fixture(
        {
            "assessment_id": "res-sat",
            "resonance_class": "saturated",
        }
    )
    result = evaluate_resonance_assessment(assessment)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "sbs.advisory.signal_saturation_detected"


def test_record_hash_stable() -> None:
    a = signal_from_fixture({"signal_id": "stable"})
    b = signal_from_fixture({"signal_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        SemanticSignal(
            signal_id="bad",
            emitter_id="password=secret",
            emitter_type="agent0",
            signal_class="presence",
            semantic_level="operational",
            polarity=0.0,
            magnitude=0.5,
            urgency="low",
            proximity="same_runtime",
            context_distance=0.1,
            evidence_refs=(),
            event_head="rtc:head",
            world_state_hash="ws:fixture",
            created_at=FIXTURE_CLOCK,
            expires_at="2026-06-13T23:00:00.000000Z",
        )


def test_sbs_event_refs_no_authority_fields() -> None:
    refs = planned_sbs_event_refs()
    assert len(refs) >= 13
    assert all(not e.get("authority_fields") for e in refs)


def test_unknown_signal_refused() -> None:
    signal = signal_from_fixture({"signal_id": "sbs-unk", "signal_class": "unknown"})
    result = evaluate_semantic_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sbs.refused.incompatible_signal"


def test_resonance_recorded_positive() -> None:
    assessment = resonance_from_fixture({"assessment_id": "res-ok"})
    result = evaluate_resonance_assessment(assessment)
    assert result["status"] == "recorded"
    assert result["resonance_is_not_consent"] is True
