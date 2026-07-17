"""PUB typed schemas — publication is an external action."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

PUB_SCHEMA_VERSION = "1.0"

Classification = Literal[
    "public",
    "public_redacted",
    "internal",
    "restricted",
    "hold",
    "forbidden",
    "unknown",
]


@dataclass(frozen=True)
class PublicationReview:
    review_id: str
    artifact_refs: tuple[str, ...]
    classification: Classification
    reason_codes: tuple[str, ...]
    secret_scan_refs: tuple[str, ...]
    dangerous_detail_refs: tuple[str, ...]
    claim_evidence_refs: tuple[str, ...]
    redaction_required: bool
    operator_approval_required: bool
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_review_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pub-publication-review",
            "schema_version": PUB_SCHEMA_VERSION,
            "review_id": self.review_id,
            "artifact_refs": list(self.artifact_refs),
            "classification": self.classification,
            "reason_codes": list(self.reason_codes),
            "secret_scan_refs": list(self.secret_scan_refs),
            "dangerous_detail_refs": list(self.dangerous_detail_refs),
            "claim_evidence_refs": list(self.claim_evidence_refs),
            "redaction_required": self.redaction_required,
            "operator_approval_required": self.operator_approval_required,
            "created_at": self.created_at,
            "expiry": self.expiry,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_review_fields(review: PublicationReview) -> None:
    if not review.review_id.strip():
        raise RuntimeContextValidationError("pub.validation.review_id", "review_id required")
    if not review.artifact_refs:
        raise RuntimeContextValidationError("pub.validation.artifact_refs", "artifact_refs required")
    for ref in review.artifact_refs:
        if "password=" in ref.lower() or "api_key=" in ref.lower():
            raise RuntimeContextValidationError("pub.validation.secret", "secrets forbidden in artifact refs")


def review_from_fixture(fixture: dict[str, str]) -> PublicationReview:
    return PublicationReview(
        review_id=fixture["review_id"],
        artifact_refs=tuple(fixture.get("artifact_refs", "docs/reports/phases/CT-A_AUDIT.md").split("|")),
        classification=fixture.get("classification", "internal"),  # type: ignore[arg-type]
        reason_codes=tuple(fixture.get("reason_codes", "fixture").split("|")),
        secret_scan_refs=tuple(fixture.get("secret_scan_refs", "").split("|")) if fixture.get("secret_scan_refs") else (),
        dangerous_detail_refs=tuple(
            fixture.get("dangerous_detail_refs", "").split("|")
        )
        if fixture.get("dangerous_detail_refs")
        else (),
        claim_evidence_refs=tuple(
            fixture.get("claim_evidence_refs", "").split("|")
        )
        if fixture.get("claim_evidence_refs")
        else (),
        redaction_required=fixture.get("redaction_required", "0") == "1",
        operator_approval_required=fixture.get("operator_approval_required", "1") == "1",
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T20:00:00.000000Z"),
    )


__all__ = [
    "Classification",
    "PUB_SCHEMA_VERSION",
    "PublicationReview",
    "review_from_fixture",
    "validate_review_fields",
]
