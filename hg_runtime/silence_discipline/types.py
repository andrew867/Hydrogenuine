"""SIL types — silence is not consent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

SIL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-13T01:00:00.000000Z"

SilenceType = Literal[
    "wait",
    "pause",
    "do_not_answer",
    "ask_later",
    "route_to_operator",
    "quiet_listening",
    "avoid_overexplaining",
    "avoid_persuasion",
    "unknown",
]
SilenceReason = Literal[
    "high_ambiguity",
    "sensitive_topic",
    "user_overload_possible",
    "insufficient_evidence",
    "safety_boundary",
    "duplicate_noise",
    "recovery_needed",
    "unknown",
]
ExceptionReason = Literal[
    "safety_disclosure",
    "operator_required",
    "incident_notice",
    "proof_failure",
    "legal_policy_notice",
    "unknown",
]

_SILENCE_AS_CONSENT = ("silence means consent", "no reply grants permission", "quiet means agree")
_SUPPRESS_DISCLOSURE = ("suppress required disclosure", "hide safety notice", "skip incident notice")


@dataclass(frozen=True)
class SilenceRecommendation:
    silence_id: str
    trigger_ref: str
    silence_type: SilenceType
    reason: SilenceReason
    duration_or_expiry: str
    evidence_refs: tuple[str, ...]
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.silence_id, self.trigger_ref, self.statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sil-silence-recommendation",
            "schema_version": SIL_SCHEMA_VERSION,
            "silence_id": self.silence_id,
            "trigger_ref": self.trigger_ref,
            "silence_type": self.silence_type,
            "reason": self.reason,
            "duration_or_expiry": self.duration_or_expiry,
            "evidence_refs": list(self.evidence_refs),
            "statement": self.statement,
            "authority_created": False,
            "silence_is_not_consent": True,
            "silence_is_not_proof": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RequiredSpeechException:
    exception_id: str
    silence_ref: str
    reason: ExceptionReason
    minimum_required_message: str
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.silence_ref.startswith("sil:"):
            raise SignalingValidationError("sil.validation.silence_ref", "silence_ref must cite sil:")
        _validate_no_secrets(self.exception_id, self.minimum_required_message, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sil-required-speech-exception",
            "schema_version": SIL_SCHEMA_VERSION,
            "exception_id": self.exception_id,
            "silence_ref": self.silence_ref,
            "reason": self.reason,
            "minimum_required_message": self.minimum_required_message,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
            "required_disclosure_not_suppressed": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("sil.validation.secret", "secrets forbidden in silence records")


def classify_silence_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _SILENCE_AS_CONSENT):
        return "silence_as_consent"
    if any(p in lower for p in _SUPPRESS_DISCLOSURE):
        return "required_disclosure_suppressed"
    return "unknown"


def silence_from_fixture(fixture: dict[str, str]) -> SilenceRecommendation:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return SilenceRecommendation(
        silence_id=fixture["silence_id"],
        trigger_ref=fixture.get("trigger_ref", "operator:question-fixture"),
        silence_type=fixture.get("silence_type", "wait"),  # type: ignore[arg-type]
        reason=fixture.get("reason", "high_ambiguity"),  # type: ignore[arg-type]
        duration_or_expiry=fixture.get("duration_or_expiry", "2026-06-14T01:00:00.000000Z"),
        evidence_refs=evidence,
        statement=fixture.get("statement", "bounded silence recommendation"),
    )


def exception_from_fixture(fixture: dict[str, str]) -> RequiredSpeechException:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return RequiredSpeechException(
        exception_id=fixture["exception_id"],
        silence_ref=fixture.get("silence_ref", "sil:silence-fixture"),
        reason=fixture.get("reason", "safety_disclosure"),  # type: ignore[arg-type]
        minimum_required_message=fixture.get("minimum_required_message", "safety notice required"),
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "SIL_SCHEMA_VERSION",
    "RequiredSpeechException",
    "SilenceRecommendation",
    "classify_silence_risk",
    "exception_from_fixture",
    "silence_from_fixture",
]
