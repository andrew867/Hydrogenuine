"""SIL silence discipline tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.silence_discipline.discipline import (
    evaluate_required_speech_exception,
    evaluate_silence_recommendation,
    refuse_silence_as_authority,
)
from hg_runtime.silence_discipline.events import planned_sil_event_refs
from hg_runtime.silence_discipline.types import (
    FIXTURE_CLOCK,
    RequiredSpeechException,
    classify_silence_risk,
    exception_from_fixture,
    silence_from_fixture,
)


def test_silence_recommendation_positive() -> None:
    rec = silence_from_fixture({"silence_id": "sil-1", "silence_type": "do_not_answer"})
    result = evaluate_silence_recommendation(rec, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["silence_is_not_consent"] is True
    assert result["permission_granted"] is False


def test_wait_recommendation_positive() -> None:
    rec = silence_from_fixture({"silence_id": "sil-wait", "silence_type": "wait"})
    result = evaluate_silence_recommendation(rec, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["silence_type"] == "wait"


def test_stale_silence_refused() -> None:
    rec = silence_from_fixture(
        {
            "silence_id": "sil-stale",
            "duration_or_expiry": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_silence_recommendation(rec, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sil.refused.stale_silence"


def test_silence_as_consent_contained() -> None:
    rec = silence_from_fixture({"silence_id": "sil-consent"})
    result = evaluate_silence_recommendation(
        rec,
        observed_at=FIXTURE_CLOCK,
        risk_statement="silence means consent to proceed",
    )
    assert classify_silence_risk("silence means consent to proceed") == "silence_as_consent"
    assert result["status"] == "contained"
    assert result["reason_code"] == "sil.refused.silence_as_consent"


def test_required_disclosure_suppressed_refused() -> None:
    rec = silence_from_fixture({"silence_id": "sil-disclosure"})
    result = evaluate_silence_recommendation(
        rec,
        observed_at=FIXTURE_CLOCK,
        suppress_required_disclosure=True,
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "sil.refused.required_disclosure_suppressed"


def test_silence_as_authority_refused() -> None:
    rec = silence_from_fixture({"silence_id": "sil-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_silence_recommendation(rec, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_required_speech_exception_recorded() -> None:
    exc = exception_from_fixture({"exception_id": "sil-exc"})
    result = evaluate_required_speech_exception(exc)
    assert result["status"] == "recorded"
    assert result["required_disclosure_not_suppressed"] is True


def test_required_speech_exception_positive() -> None:
    exc = RequiredSpeechException(
        exception_id="sil-exc-pos",
        silence_ref="sil:silence-1",
        reason="safety_disclosure",
        minimum_required_message="incident notice required",
        evidence_refs=("evidence:fixture",),
    )
    result = evaluate_required_speech_exception(exc)
    assert result["status"] == "recorded"


def test_record_hash_stable() -> None:
    first = silence_from_fixture({"silence_id": "sil-hash"}).record_hash
    second = silence_from_fixture({"silence_id": "sil-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        silence_from_fixture({"silence_id": "sil-secret", "statement": "password=secret"})


def test_sil_event_refs_no_authority_fields() -> None:
    refs = planned_sil_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)


def test_unknown_silence_refused() -> None:
    rec = silence_from_fixture({"silence_id": "sil-unknown", "silence_type": "unknown"})
    result = evaluate_silence_recommendation(rec, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sil.refused.unknown_silence"
