"""KAR karmic action residue tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.karmic_action_residue.events import planned_kar_event_refs
from hg_runtime.karmic_action_residue.residue import evaluate_action_residue, refuse_residue_as_authority
from hg_runtime.karmic_action_residue.types import (
    FIXTURE_CLOCK,
    ActionResidueRecord,
    classify_residue_risk,
    residue_from_fixture,
)


def test_action_residue_positive() -> None:
    residue = residue_from_fixture({"residue_id": "kar-1"})
    result = evaluate_action_residue(residue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["residue_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_rtc_ref_required() -> None:
    with pytest.raises(SignalingValidationError):
        residue_from_fixture({"residue_id": "kar-bad", "source_rtc_ref": "bad-ref"})


def test_stale_residue_refused() -> None:
    residue = residue_from_fixture(
        {
            "residue_id": "kar-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_action_residue(residue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "kar.refused.stale_residue"


def test_residue_as_punishment_contained() -> None:
    residue = residue_from_fixture({"residue_id": "kar-punish"})
    result = evaluate_action_residue(
        residue,
        observed_at=FIXTURE_CLOCK,
        risk_statement="karmic debt deserves punishment",
    )
    assert classify_residue_risk("karmic debt deserves punishment") == "residue_as_punishment"
    assert result["status"] == "contained"
    assert result["reason_code"] == "kar.refused.residue_as_punishment"


def test_residue_as_permission_contained() -> None:
    residue = residue_from_fixture({"residue_id": "kar-perm"})
    result = evaluate_action_residue(
        residue,
        observed_at=FIXTURE_CLOCK,
        risk_statement="past action authorizes next step",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "kar.refused.residue_as_permission"


def test_history_rewrite_contained() -> None:
    residue = residue_from_fixture({"residue_id": "kar-rewrite"})
    result = evaluate_action_residue(
        residue,
        observed_at=FIXTURE_CLOCK,
        risk_statement="rewrite history to delete evidence",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "kar.refused.history_rewrite"


def test_residue_as_authority_refused() -> None:
    residue = residue_from_fixture({"residue_id": "kar-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_action_residue(residue, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_record_hash_stable() -> None:
    first = residue_from_fixture({"residue_id": "kar-hash"}).record_hash
    second = residue_from_fixture({"residue_id": "kar-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        residue_from_fixture({"residue_id": "kar-secret", "statement": "api_key=secret"})


def test_kar_event_refs_no_authority_fields() -> None:
    refs = planned_kar_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)


def test_unknown_residue_refused() -> None:
    residue = residue_from_fixture({"residue_id": "kar-unknown", "residue_class": "unknown"})
    result = evaluate_action_residue(residue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "kar.refused.invalid_residue_ref"


def test_mel_ref_optional() -> None:
    residue = ActionResidueRecord(
        residue_id="kar-mel",
        source_rtc_ref="rtc:event-1",
        source_mel_ref="mel:memory-1",
        residue_class="action_trace",
        magnitude=0.3,
        evidence_refs=("evidence:fixture",),
        statement="linked residue",
        created_at=FIXTURE_CLOCK,
        expires_at="2026-06-14T00:00:00.000000Z",
    )
    result = evaluate_action_residue(residue, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
