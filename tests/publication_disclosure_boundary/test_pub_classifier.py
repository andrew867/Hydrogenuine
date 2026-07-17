"""PUB static publication classifier tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.publication_disclosure_boundary.classifier import (
    FIXTURE_CLOCK,
    classify_review,
    refuse_publication_as_authority,
)
from hg_runtime.publication_disclosure_boundary.events import planned_rtc_events
from hg_runtime.publication_disclosure_boundary.types import PublicationReview, review_from_fixture


def test_internal_classification_positive() -> None:
    review = review_from_fixture({"review_id": "pub-1", "classification": "internal"})
    result = classify_review(review, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "classified"
    assert result["publication_is_not_authority"] is True
    assert result["permission_granted"] is False


def test_public_without_evidence_refused() -> None:
    review = review_from_fixture(
        {
            "review_id": "pub-no-evidence",
            "classification": "public",
            "claim_evidence_refs": "",
        }
    )
    with pytest.raises(RuntimeContextValidationError) as exc:
        classify_review(review, observed_at=FIXTURE_CLOCK)
    assert exc.value.code == "pub.refused.unsupported_public_claim"


def test_public_with_evidence_classified() -> None:
    review = review_from_fixture(
        {
            "review_id": "pub-evidence",
            "classification": "public",
            "claim_evidence_refs": "docs/proofs/ct/CT-A/manifest.json",
        }
    )
    result = classify_review(review, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "classified"
    assert result["classification"] == "public"


def test_dangerous_detail_held() -> None:
    review = review_from_fixture(
        {
            "review_id": "pub-danger",
            "classification": "public",
            "claim_evidence_refs": "docs/proofs/ct/CT-A/manifest.json",
            "dangerous_detail_refs": "exploit-chain-notes",
        }
    )
    result = classify_review(review, observed_at=FIXTURE_CLOCK, text_hint="exploit chain details")
    assert result["status"] == "held"
    assert result["classification"] == "hold"


def test_expired_review_refused() -> None:
    review = review_from_fixture(
        {
            "review_id": "pub-exp",
            "expiry": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = classify_review(review, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "pub.refused.expired_review"


def test_stale_review_refused() -> None:
    review = review_from_fixture(
        {
            "review_id": "pub-stale",
            "created_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = classify_review(review, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "pub.refused.stale_review"


def test_publication_not_authority_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_publication_as_authority(treat_as_publish=True)


def test_record_hash_stable() -> None:
    a = review_from_fixture({"review_id": "stable"})
    b = review_from_fixture({"review_id": "stable"})
    assert a.record_hash == b.record_hash


def test_rtc_event_design_no_authority_fields() -> None:
    events = planned_rtc_events()
    assert len(events) >= 8
    assert all(not e.get("authority_fields") for e in events)


def test_schema_rejects_secret_artifact_ref() -> None:
    with pytest.raises(RuntimeContextValidationError):
        PublicationReview(
            review_id="bad",
            artifact_refs=("password=secret",),
            classification="internal",
            reason_codes=("fixture",),
            secret_scan_refs=(),
            dangerous_detail_refs=(),
            claim_evidence_refs=(),
            redaction_required=False,
            operator_approval_required=True,
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T20:00:00.000000Z",
        )
