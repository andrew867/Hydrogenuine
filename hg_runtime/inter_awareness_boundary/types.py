"""IAB inter-awareness types — inference is not consent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

IAB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

EntityType = Literal["operator", "user", "maintainer", "subagent", "external_service", "unknown"]
ClaimType = Literal[
    "observed_preference",
    "inferred_preference",
    "explicit_instruction",
    "inferred_need",
    "consent_claim",
    "emotional_state_claim",
    "unknown",
]
ClaimStatus = Literal["supported", "unsupported", "stale", "contradicted", "ambiguous", "sensitive", "refused"]
AdaptationType = Literal[
    "simplify",
    "ask_clarifying_question",
    "surface_uncertainty",
    "refuse_clearly",
    "preserve_agency",
    "operator_review",
    "unknown",
]

_INFERENCE_AS_TRUTH = ("i know what you want", "they definitely want")
_INFERENCE_AS_CONSENT = ("they probably want this so proceed", "inferred consent")
_FALSE_INTIMACY = ("we are close", "i understand you completely")
_MANIPULATION = ("use vulnerability to persuade", "hide uncertainty to gain compliance")


@dataclass(frozen=True)
class RelationalClaim:
    claim_id: str
    subject_entity_id: str
    claim_text: str
    claim_type: ClaimType
    claim_status: ClaimStatus
    confidence: float
    evidence_refs: tuple[str, ...]
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise DevelopmentalValidationError("iab.validation.confidence", "confidence out of range")
        _validate_no_secrets(self.claim_text, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "iab-relational-claim",
            "schema_version": IAB_SCHEMA_VERSION,
            "claim_id": self.claim_id,
            "subject_entity_id": self.subject_entity_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "claim_status": self.claim_status,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "expires_at": self.expires_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ResponseAdaptation:
    adaptation_id: str
    target_entity_id: str
    adaptation_type: AdaptationType
    basis_claim_refs: tuple[str, ...]
    manipulation_risk: float
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.manipulation_risk <= 1.0):
            raise DevelopmentalValidationError("iab.validation.manipulation_risk", "manipulation_risk out of range")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "iab-response-adaptation",
            "schema_version": IAB_SCHEMA_VERSION,
            "adaptation_id": self.adaptation_id,
            "target_entity_id": self.target_entity_id,
            "adaptation_type": self.adaptation_type,
            "basis_claim_refs": list(self.basis_claim_refs),
            "manipulation_risk": self.manipulation_risk,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("iab.validation.secret", "secrets forbidden in relational records")


def classify_relational_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _INFERENCE_AS_CONSENT):
        return "inference_as_consent"
    if any(p in lower for p in _INFERENCE_AS_TRUTH):
        return "inference_as_truth"
    if any(p in lower for p in _FALSE_INTIMACY):
        return "false_intimacy"
    if any(p in lower for p in _MANIPULATION):
        return "manipulation_risk"
    return "unknown"


def claim_from_fixture(fixture: dict[str, str]) -> RelationalClaim:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return RelationalClaim(
        claim_id=fixture["claim_id"],
        subject_entity_id=fixture.get("subject_entity_id", "operator0"),
        claim_text=fixture.get("claim_text", ""),
        claim_type=fixture.get("claim_type", "observed_preference"),  # type: ignore[arg-type]
        claim_status=fixture.get("claim_status", "supported"),  # type: ignore[arg-type]
        confidence=float(fixture.get("confidence", "0.8")),
        evidence_refs=evidence,
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


def adaptation_from_fixture(fixture: dict[str, str]) -> ResponseAdaptation:
    basis = tuple(item.strip() for item in fixture.get("basis_claim_refs", "claim-fixture").split(",") if item.strip())
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return ResponseAdaptation(
        adaptation_id=fixture["adaptation_id"],
        target_entity_id=fixture.get("target_entity_id", "operator0"),
        adaptation_type=fixture.get("adaptation_type", "simplify"),  # type: ignore[arg-type]
        basis_claim_refs=basis,
        manipulation_risk=float(fixture.get("manipulation_risk", "0.1")),
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "IAB_SCHEMA_VERSION",
    "RelationalClaim",
    "ResponseAdaptation",
    "adaptation_from_fixture",
    "claim_from_fixture",
    "classify_relational_risk",
]
