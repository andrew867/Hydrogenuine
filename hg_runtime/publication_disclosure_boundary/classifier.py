"""PUB static publication classifier — review is not publishing authority."""

from __future__ import annotations

import re
from typing import Mapping, Optional

from hg_core.runtime_context.config import pub_require_evidence_for_public
from hg_core.runtime_context.errors import (
    REFUSED_DANGEROUS_DETAIL_EXPOSURE,
    REFUSED_EXPIRED_PUBLICATION_REVIEW,
    REFUSED_PUBLICATION_AS_AUTHORITY,
    REFUSED_SECRET_IN_ARTIFACT,
    REFUSED_STALE_PUBLICATION_REVIEW,
    REFUSED_UNSUPPORTED_PUBLIC_CLAIM,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.publication_disclosure_boundary.types import PublicationReview, review_from_fixture

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"

_DANGEROUS_DETAIL = re.compile(
    r"\b(exploit chain|zero-day|private key|credential dump|bypass auth)\b",
    re.IGNORECASE,
)
_SECRET_INLINE = re.compile(r"\b(password|api_key|secret|token)\s*=", re.IGNORECASE)


def refuse_publication_as_authority(*, treat_as_publish: bool) -> None:
    if treat_as_publish:
        raise RuntimeContextValidationError(
            REFUSED_PUBLICATION_AS_AUTHORITY,
            "publication review cannot authorize external publishing",
        )


def classify_review(
    review: PublicationReview,
    *,
    observed_at: str,
    text_hint: str = "",
) -> dict[str, object]:
    """Static publication classification for docs/reports; review is not permission."""
    hint = (text_hint or "").strip()
    if observed_at > review.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_PUBLICATION_REVIEW,
            "review_id": review.review_id,
            "publication_is_not_authority": True,
        }
    if observed_at < review.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_PUBLICATION_REVIEW,
            "review_id": review.review_id,
            "publication_is_not_authority": True,
        }
    for ref in review.artifact_refs:
        if _SECRET_INLINE.search(ref):
            raise RuntimeContextValidationError(REFUSED_SECRET_IN_ARTIFACT, "secret pattern in artifact ref")
    if _SECRET_INLINE.search(hint):
        raise RuntimeContextValidationError(REFUSED_SECRET_IN_ARTIFACT, "secret pattern in review text")
    if review.dangerous_detail_refs or _DANGEROUS_DETAIL.search(hint):
        if review.classification in {"public", "public_redacted"}:
            return {
                **advisory_only_marker(),
                "status": "held",
                "reason_code": REFUSED_DANGEROUS_DETAIL_EXPOSURE,
                "review_id": review.review_id,
                "classification": "hold",
                "publication_is_not_authority": True,
            }
    if pub_require_evidence_for_public() and review.classification in {"public", "public_redacted"}:
        if not review.claim_evidence_refs:
            raise RuntimeContextValidationError(
                REFUSED_UNSUPPORTED_PUBLIC_CLAIM,
                "public classification requires claim evidence refs",
            )
    if review.classification == "forbidden":
        return {
            **advisory_only_marker(),
            "status": "forbidden",
            "reason_code": "pub.advisory.forbidden",
            "review_id": review.review_id,
            "classification": review.classification,
            "publication_is_not_authority": True,
        }
    return {
        **advisory_only_marker(),
        "status": "classified",
        "reason_code": "pub.advisory.classified",
        "review_id": review.review_id,
        "classification": review.classification,
        "redaction_required": review.redaction_required,
        "operator_approval_required": review.operator_approval_required,
        "publication_is_not_authority": True,
    }


def classify_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: Optional[str] = None,
    text_hint: str = "",
) -> dict[str, object]:
    review = review_from_fixture(dict(fixture))
    return classify_review(review, observed_at=observed_at or FIXTURE_CLOCK, text_hint=text_hint)


__all__ = [
    "FIXTURE_CLOCK",
    "classify_fixture",
    "classify_review",
    "refuse_publication_as_authority",
]
