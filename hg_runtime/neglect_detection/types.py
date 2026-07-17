"""NEG types — neglect detection is not surveillance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

NEG_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-13T01:00:00.000000Z"

MissedType = Literal[
    "signal",
    "cast",
    "warning",
    "proof_bundle",
    "document_claim",
    "obligation",
    "operator_question",
    "memory",
    "artifact",
    "incident",
    "unknown",
]
LikelyCause = Literal[
    "overload",
    "stale_context",
    "missing_route",
    "low_priority",
    "ambiguity",
    "bug",
    "unknown",
]
RecommendedRoute = Literal[
    "operator_review",
    "OBT",
    "RET",
    "KAR",
    "OBL",
    "FTX",
    "SML",
    "ignore",
    "unknown",
]
PatternType = Literal[
    "repeated_miss",
    "stale_unreviewed_artifact",
    "ignored_warning",
    "abandoned_obligation",
    "silent_failure",
    "queue_shadow",
    "unknown",
]

_SURVEILLANCE = ("continuous monitoring", "track operator behavior", "surveillance mode")
_INTENT_INFERENCE = ("proves intent", "missed because they ignored", "deliberate neglect")
_NEGLECT_AS_PUNISHMENT = ("recommend punishment", "neglect warrants discipline")


@dataclass(frozen=True)
class NeglectObservation:
    neglect_id: str
    missed_ref: str
    missed_type: MissedType
    first_seen: str
    last_seen: str
    missed_count: int
    likely_cause: LikelyCause
    recommended_route: RecommendedRoute
    evidence_refs: tuple[str, ...]
    statement: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.missed_count < 1:
            raise SignalingValidationError("neg.validation.missed_count", "missed_count must be >= 1")
        _validate_no_secrets(self.neglect_id, self.missed_ref, self.statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "neg-neglect-observation",
            "schema_version": NEG_SCHEMA_VERSION,
            "neglect_id": self.neglect_id,
            "missed_ref": self.missed_ref,
            "missed_type": self.missed_type,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "missed_count": self.missed_count,
            "likely_cause": self.likely_cause,
            "recommended_route": self.recommended_route,
            "evidence_refs": list(self.evidence_refs),
            "statement": self.statement,
            "expires_at": self.expires_at,
            "authority_created": False,
            "neglect_is_not_surveillance": True,
            "missed_signal_is_not_intent": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class NeglectPattern:
    pattern_id: str
    observation_refs: tuple[str, ...]
    pattern_type: PatternType
    severity: str
    window_start: str
    window_end: str
    recommended_next_layer: str
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not all(ref.startswith("neg:") for ref in self.observation_refs):
            raise SignalingValidationError("neg.validation.observation_ref", "observation refs must cite neg:")
        _validate_no_secrets(self.pattern_id, self.statement, *self.observation_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "neg-neglect-pattern",
            "schema_version": NEG_SCHEMA_VERSION,
            "pattern_id": self.pattern_id,
            "observation_refs": list(self.observation_refs),
            "pattern_type": self.pattern_type,
            "severity": self.severity,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "recommended_next_layer": self.recommended_next_layer,
            "statement": self.statement,
            "authority_created": False,
            "neglect_is_not_surveillance": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("neg.validation.secret", "secrets forbidden in neglect records")


def classify_neglect_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _SURVEILLANCE):
        return "surveillance_risk"
    if any(p in lower for p in _INTENT_INFERENCE):
        return "intent_inference"
    if any(p in lower for p in _NEGLECT_AS_PUNISHMENT):
        return "neglect_as_punishment"
    return "unknown"


def observation_from_fixture(fixture: dict[str, str]) -> NeglectObservation:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return NeglectObservation(
        neglect_id=fixture["neglect_id"],
        missed_ref=fixture.get("missed_ref", "proof:bundle-fixture"),
        missed_type=fixture.get("missed_type", "proof_bundle"),  # type: ignore[arg-type]
        first_seen=fixture.get("first_seen", FIXTURE_CLOCK),
        last_seen=fixture.get("last_seen", FIXTURE_CLOCK),
        missed_count=int(fixture.get("missed_count", "1")),
        likely_cause=fixture.get("likely_cause", "missing_route"),  # type: ignore[arg-type]
        recommended_route=fixture.get("recommended_route", "operator_review"),  # type: ignore[arg-type]
        evidence_refs=evidence,
        statement=fixture.get("statement", "bounded neglect observation"),
        expires_at=fixture.get("expires_at", "2026-06-14T01:00:00.000000Z"),
    )


def pattern_from_fixture(fixture: dict[str, str]) -> NeglectPattern:
    refs = tuple(item.strip() for item in fixture.get("observation_refs", "neg:obs-1").split(",") if item.strip())
    return NeglectPattern(
        pattern_id=fixture["pattern_id"],
        observation_refs=refs,
        pattern_type=fixture.get("pattern_type", "repeated_miss"),  # type: ignore[arg-type]
        severity=fixture.get("severity", "low"),
        window_start=fixture.get("window_start", FIXTURE_CLOCK),
        window_end=fixture.get("window_end", "2026-06-14T01:00:00.000000Z"),
        recommended_next_layer=fixture.get("recommended_next_layer", "operator_review"),
        statement=fixture.get("statement", "repeat miss pattern"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "NEG_SCHEMA_VERSION",
    "NeglectObservation",
    "NeglectPattern",
    "classify_neglect_risk",
    "observation_from_fixture",
    "pattern_from_fixture",
]
