"""APC ambient proximity cues tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.ambient_proximity_cues.cues import evaluate_ambient_cue, refuse_cue_as_authority
from hg_runtime.ambient_proximity_cues.events import planned_apc_event_refs
from hg_runtime.ambient_proximity_cues.types import (
    FIXTURE_CLOCK,
    AmbientCue,
    classify_cue_risk,
    cue_from_fixture,
)


def test_ambient_cue_positive() -> None:
    cue = cue_from_fixture({"cue_id": "apc-1"})
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["cue_is_not_truth"] is True
    assert result["permission_granted"] is False


def test_stale_cue_refused() -> None:
    cue = cue_from_fixture(
        {
            "cue_id": "apc-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "apc.refused.stale_cue"


def test_cue_as_truth_contained() -> None:
    cue = cue_from_fixture({"cue_id": "apc-truth", "cue_text": "the cue proves it"})
    assert classify_cue_risk("the cue proves it") == "cue_as_truth"
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "apc.refused.cue_as_truth"


def test_cue_as_consent_contained() -> None:
    cue = cue_from_fixture({"cue_id": "apc-consent", "cue_text": "gesture means consent"})
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "apc.refused.cue_as_consent"


def test_emotion_diagnosis_contained() -> None:
    cue = cue_from_fixture({"cue_id": "apc-emo", "cue_text": "they are angry"})
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "apc.refused.emotion_diagnosis"


def test_treat_as_truth_contained() -> None:
    cue = cue_from_fixture({"cue_id": "apc-treat"})
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK, treat_as_truth=True)
    assert result["status"] == "contained"
    assert result["reason_code"] == "apc.refused.cue_as_truth"


def test_cue_as_authority_refused() -> None:
    cue = cue_from_fixture({"cue_id": "apc-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    with pytest.raises(SignalingValidationError):
        refuse_cue_as_authority(treat_as_authority=True)


def test_record_hash_stable() -> None:
    a = cue_from_fixture({"cue_id": "stable"})
    b = cue_from_fixture({"cue_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        AmbientCue(
            cue_id="bad",
            cue_type="proximity",
            cue_text="token=secret",
            confidence=0.5,
            ambiguity=0.5,
            evidence_refs=(),
            expires_at="2026-06-13T23:00:00.000000Z",
        )


def test_apc_event_refs_no_authority_fields() -> None:
    refs = planned_apc_event_refs()
    assert len(refs) >= 10
    assert all(not e.get("authority_fields") for e in refs)


def test_unknown_cue_refused() -> None:
    cue = cue_from_fixture({"cue_id": "apc-unk", "cue_type": "unknown"})
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "apc.refused.unknown_cue"


def test_ambiguity_preserved() -> None:
    cue = cue_from_fixture({"cue_id": "apc-amb", "ambiguity": "0.8"})
    result = evaluate_ambient_cue(cue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["ambiguity_preserved"] is True
