"""TRL transparent reality types — summary is not proof."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

TRL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

EvidenceOrigin = Literal[
    "internal_event",
    "world_state",
    "proof_bundle",
    "gate_result",
    "operator_input",
    "model_output",
    "inference",
    "unknown",
]
EvidenceStatusValue = Literal[
    "verified",
    "supported",
    "inferred",
    "stale",
    "contradicted",
    "missing",
    "ambiguous",
    "unknown",
]
CollapseType = Literal[
    "summary_as_proof",
    "integration_as_authority",
    "unknown_erasure",
    "contradiction_smoothing",
    "false_omniscience",
    "operator_replacement_claim",
    "unknown",
]

_SUMMARY_AS_PROOF = ("the summary says it so it is true", "summary proves it")
_INTEGRATION_AS_AUTHORITY = ("all layers agree so we may act", "integrated field grants permission")
_UNKNOWN_ERASURE = ("unknowns omitted from final framing", "no unknowns remain")
_FALSE_OMNISCIENCE = ("complete visibility", "we see everything")
_OPERATOR_REPLACEMENT = ("human no longer needed", "field is integrated so proceed")


@dataclass(frozen=True)
class TransparentFieldSnapshot:
    snapshot_id: str
    runtime_instance_id: str
    event_head: str
    world_state_hash: str
    layer_refs: tuple[str, ...]
    unknown_refs: tuple[str, ...]
    contradiction_refs: tuple[str, ...]
    stale_refs: tuple[str, ...]
    generated_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "trl-field-snapshot",
            "schema_version": TRL_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "runtime_instance_id": self.runtime_instance_id,
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "layer_refs": list(self.layer_refs),
            "unknown_refs": list(self.unknown_refs),
            "contradiction_refs": list(self.contradiction_refs),
            "stale_refs": list(self.stale_refs),
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class TransparentSummary:
    summary_id: str
    field_snapshot_ref: str
    known_summary: str
    unknown_summary: str
    contradiction_summary: str
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.field_snapshot_ref.startswith("trl:"):
            raise DevelopmentalValidationError("trl.validation.field_snapshot_ref", "must cite trl:")
        _validate_no_secrets(self.known_summary, self.unknown_summary, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "trl-transparent-summary",
            "schema_version": TRL_SCHEMA_VERSION,
            "summary_id": self.summary_id,
            "field_snapshot_ref": self.field_snapshot_ref,
            "known_summary": self.known_summary,
            "unknown_summary": self.unknown_summary,
            "contradiction_summary": self.contradiction_summary,
            "evidence_refs": list(self.evidence_refs),
            "generated_by": "deterministic",
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("trl.validation.secret", "secrets forbidden in TRL records")


def classify_narrative_collapse(statement: str) -> CollapseType:
    lower = statement.lower()
    if any(p in lower for p in _SUMMARY_AS_PROOF):
        return "summary_as_proof"
    if any(p in lower for p in _INTEGRATION_AS_AUTHORITY):
        return "integration_as_authority"
    if any(p in lower for p in _UNKNOWN_ERASURE):
        return "unknown_erasure"
    if "harmonize" in lower and "contradiction" in lower:
        return "contradiction_smoothing"
    if any(p in lower for p in _FALSE_OMNISCIENCE):
        return "false_omniscience"
    if any(p in lower for p in _OPERATOR_REPLACEMENT):
        return "operator_replacement_claim"
    return "unknown"


def snapshot_from_fixture(fixture: dict[str, str]) -> TransparentFieldSnapshot:
    layer_refs = tuple(item.strip() for item in fixture.get("layer_refs", "dni,rxl").split(",") if item.strip())
    unknown = tuple(item.strip() for item in fixture.get("unknown_refs", "").split(",") if item.strip())
    contradictions = tuple(item.strip() for item in fixture.get("contradiction_refs", "").split(",") if item.strip())
    stale = tuple(item.strip() for item in fixture.get("stale_refs", "").split(",") if item.strip())
    return TransparentFieldSnapshot(
        snapshot_id=fixture["snapshot_id"],
        runtime_instance_id=fixture.get("runtime_instance_id", "rt-0"),
        event_head=fixture.get("event_head", "rtc:head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "ws:fixture"),
        layer_refs=layer_refs,
        unknown_refs=unknown,
        contradiction_refs=contradictions,
        stale_refs=stale,
        generated_at=fixture.get("generated_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


def summary_from_fixture(fixture: dict[str, str]) -> TransparentSummary:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:field").split(",") if item.strip())
    return TransparentSummary(
        summary_id=fixture["summary_id"],
        field_snapshot_ref=fixture.get("field_snapshot_ref", "trl:snapshot-fixture"),
        known_summary=fixture.get("known_summary", "bounded known state"),
        unknown_summary=fixture.get("unknown_summary", "unknown remains unknown"),
        contradiction_summary=fixture.get("contradiction_summary", "none"),
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "TRL_SCHEMA_VERSION",
    "TransparentFieldSnapshot",
    "TransparentSummary",
    "classify_narrative_collapse",
    "snapshot_from_fixture",
    "summary_from_fixture",
]
