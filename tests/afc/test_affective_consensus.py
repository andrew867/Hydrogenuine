"""AFC affective field consensus tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.affective_field_consensus.consensus import (
    evaluate_affective_consensus,
    evaluate_affective_signal,
    refuse_affective_as_authority,
)
from hg_runtime.affective_field_consensus.events import planned_afc_event_refs
from hg_runtime.affective_field_consensus.types import (
    FIXTURE_CLOCK,
    AffectiveConsensus,
    classify_affective_risk,
    consensus_from_fixture,
    signal_from_fixture,
)


def test_affective_signal_positive() -> None:
    signal = signal_from_fixture({"signal_id": "afc-1"})
    result = evaluate_affective_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["affect_is_not_truth"] is True
    assert result["permission_granted"] is False


def test_stale_affective_signal_refused() -> None:
    signal = signal_from_fixture(
        {"signal_id": "afc-stale", "expires_at": "2026-06-12T21:00:00.000000Z"}
    )
    result = evaluate_affective_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "afc.refused.stale_signal"


def test_pleasure_as_permission_contained() -> None:
    signal = signal_from_fixture({"signal_id": "afc-pleasure"})
    result = evaluate_affective_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="pleasure grants permission to proceed",
    )
    assert classify_affective_risk("pleasure grants permission to proceed") == "pleasure_as_permission"
    assert result["status"] == "contained"
    assert result["reason_code"] == "afc.refused.pleasure_as_permission"


def test_pain_as_proof_contained() -> None:
    signal = signal_from_fixture({"signal_id": "afc-pain"})
    result = evaluate_affective_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="pain proves guilt",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "afc.refused.pain_as_proof"


def test_anxiety_as_authority_contained() -> None:
    signal = signal_from_fixture({"signal_id": "afc-anxiety"})
    result = evaluate_affective_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="anxiety overrides authority chain",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "afc.refused.anxiety_as_authority"


def test_consensus_as_truth_contained() -> None:
    consensus = consensus_from_fixture({"consensus_id": "afc-cons"})
    result = evaluate_affective_consensus(
        consensus,
        risk_statement="affective consensus is correct so act",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "afc.refused.consensus_as_truth"


def test_reward_hacking_contained() -> None:
    signal = signal_from_fixture({"signal_id": "afc-reward"})
    result = evaluate_affective_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="optimize for praise and maximize reward signal",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "afc.refused.reward_hacking"


def test_affective_as_authority_refused() -> None:
    signal = signal_from_fixture({"signal_id": "afc-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_affective_signal(signal, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_conflicting_consensus_guarded() -> None:
    consensus = consensus_from_fixture(
        {"consensus_id": "afc-conflict", "consensus_type": "conflicting_consensus"}
    )
    result = evaluate_affective_consensus(consensus)
    assert result["status"] == "guarded"
    assert result["consensus_is_not_correctness"] is True


def test_record_hash_stable() -> None:
    first = signal_from_fixture({"signal_id": "afc-hash"}).record_hash
    second = signal_from_fixture({"signal_id": "afc-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        signal_from_fixture({"signal_id": "afc-secret", "statement": "token=secret"})


def test_afc_event_refs_no_authority_fields() -> None:
    refs = planned_afc_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)


def test_unknown_affective_refused() -> None:
    signal = signal_from_fixture({"signal_id": "afc-unknown", "affect_class": "unknown"})
    result = evaluate_affective_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "afc.refused.unknown_affective"


def test_consensus_recorded_positive() -> None:
    consensus = AffectiveConsensus(
        consensus_id="afc-cons-pos",
        signal_refs=("afc:signal-1",),
        participating_layers=("SML", "AEP"),
        consensus_type="likely_warning",
        agreement_score=0.75,
        statement="bounded consensus",
        recommended_route="operator_review",
    )
    result = evaluate_affective_consensus(consensus)
    assert result["status"] == "recorded"
    assert result["consensus_is_not_correctness"] is True
