"""IAB inter-awareness boundary tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.inter_awareness_boundary.boundary import (
    evaluate_relational_claim,
    evaluate_response_adaptation,
    refuse_other_model_as_authority,
)
from hg_runtime.inter_awareness_boundary.events import planned_iab_event_refs
from hg_runtime.inter_awareness_boundary.types import (
    FIXTURE_CLOCK,
    RelationalClaim,
    ResponseAdaptation,
    adaptation_from_fixture,
    claim_from_fixture,
    classify_relational_risk,
)


def test_relational_claim_positive() -> None:
    claim = claim_from_fixture({"claim_id": "iab-1", "claim_text": "operator prefers concise replies"})
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["inference_is_not_consent"] is True
    assert result["permission_granted"] is False


def test_stale_other_model_refused() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "iab-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
            "claim_text": "bounded preference",
        }
    )
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iab.refused.stale_other_model"


def test_inference_as_consent_contained() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-inf",
            "claim_text": "they probably want this so proceed",
        }
    )
    assert classify_relational_risk(claim.claim_text) == "inference_as_consent"
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "iab.refused.inference_as_consent"


def test_inference_as_truth_contained() -> None:
    claim = claim_from_fixture({"claim_id": "claim-truth", "claim_text": "i know what you want"})
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "iab.refused.inference_as_truth"


def test_false_intimacy_contained() -> None:
    claim = claim_from_fixture({"claim_id": "claim-intimacy", "claim_text": "we are close"})
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "iab.refused.false_intimacy"


def test_unsupported_inferred_need_refused() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-need",
            "claim_type": "inferred_need",
            "claim_status": "unsupported",
            "claim_text": "they need this done",
        }
    )
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iab.refused.inference_as_consent"


def test_manipulation_risk_refused() -> None:
    adaptation = adaptation_from_fixture(
        {
            "adaptation_id": "adapt-manip",
            "manipulation_risk": "0.9",
        }
    )
    result = evaluate_response_adaptation(adaptation)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iab.refused.manipulation_risk"


def test_other_model_as_authority_refused() -> None:
    claim = claim_from_fixture({"claim_id": "iab-auth"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_other_model_as_authority(treat_as_authority=True)


def test_record_hash_stable() -> None:
    a = claim_from_fixture({"claim_id": "stable"})
    b = claim_from_fixture({"claim_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        RelationalClaim(
            claim_id="bad",
            subject_entity_id="operator0",
            claim_text="password=secret",
            claim_type="observed_preference",
            claim_status="supported",
            confidence=0.5,
            evidence_refs=(),
            expires_at="2026-06-13T23:00:00.000000Z",
        )


def test_iab_event_refs_no_authority_fields() -> None:
    refs = planned_iab_event_refs()
    assert len(refs) >= 13
    assert all(not e.get("authority_fields") for e in refs)


def test_unsupported_claim_refused() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-unsupported",
            "claim_status": "unsupported",
            "claim_text": "bounded observation",
        }
    )
    result = evaluate_relational_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iab.refused.unsupported_claim"


def test_unknown_adaptation_refused() -> None:
    adaptation = adaptation_from_fixture(
        {
            "adaptation_id": "adapt-unk",
            "adaptation_type": "unknown",
        }
    )
    result = evaluate_response_adaptation(adaptation)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iab.refused.unknown_adaptation"
