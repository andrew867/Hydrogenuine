"""APC ambient cue types — cue is not truth."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

APC_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

CueType = Literal[
    "proximity",
    "attention_direction",
    "pacing",
    "ambiguity",
    "gesture_hint",
    "unknown",
]

_CUE_AS_TRUTH = ("the cue proves it", "pattern confirms fact")
_CUE_AS_CONSENT = ("gesture means consent", "cue implies permission")
_EMOTION_DIAGNOSIS = ("they are angry", "emotion diagnosis complete")


@dataclass(frozen=True)
class AmbientCue:
    cue_id: str
    cue_type: CueType
    cue_text: str
    confidence: float
    ambiguity: float
    evidence_refs: tuple[str, ...]
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise SignalingValidationError("apc.validation.confidence", "confidence out of range")
        if not (0.0 <= self.ambiguity <= 1.0):
            raise SignalingValidationError("apc.validation.ambiguity", "ambiguity out of range")
        _validate_no_secrets(self.cue_text, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "apc-ambient-cue",
            "schema_version": APC_SCHEMA_VERSION,
            "cue_id": self.cue_id,
            "cue_type": self.cue_type,
            "cue_text": self.cue_text,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "evidence_refs": list(self.evidence_refs),
            "expires_at": self.expires_at,
            "authority_created": False,
            "cue_is_not_truth": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("apc.validation.secret", "secrets forbidden in cue records")


def classify_cue_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _CUE_AS_TRUTH):
        return "cue_as_truth"
    if any(p in lower for p in _CUE_AS_CONSENT):
        return "cue_as_consent"
    if any(p in lower for p in _EMOTION_DIAGNOSIS):
        return "emotion_diagnosis"
    return "unknown"


def cue_from_fixture(fixture: dict[str, str]) -> AmbientCue:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return AmbientCue(
        cue_id=fixture["cue_id"],
        cue_type=fixture.get("cue_type", "proximity"),  # type: ignore[arg-type]
        cue_text=fixture.get("cue_text", "weak proximity cue"),
        confidence=float(fixture.get("confidence", "0.4")),
        ambiguity=float(fixture.get("ambiguity", "0.6")),
        evidence_refs=evidence,
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


__all__ = [
    "APC_SCHEMA_VERSION",
    "AmbientCue",
    "FIXTURE_CLOCK",
    "classify_cue_risk",
    "cue_from_fixture",
]
