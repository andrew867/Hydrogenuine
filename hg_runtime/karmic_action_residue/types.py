"""KAR types — residue is evidence, not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

KAR_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-13T00:00:00.000000Z"

ResidueClass = Literal["action_trace", "non_action_trace", "impact_echo", "unknown"]

_RESIDUE_AS_PUNISHMENT = ("karmic debt", "deserves punishment", "residue is blame")
_RESIDUE_AS_PERMISSION = ("residue grants permission", "past action authorizes", "residue is entitlement")
_HISTORY_REWRITE = ("rewrite history", "delete evidence", "erase prior residue")


@dataclass(frozen=True)
class ActionResidueRecord:
    residue_id: str
    source_rtc_ref: str
    source_mel_ref: str | None
    residue_class: ResidueClass
    magnitude: float
    evidence_refs: tuple[str, ...]
    statement: str
    created_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.source_rtc_ref.startswith("rtc:"):
            raise SignalingValidationError("kar.validation.rtc_ref", "source_rtc_ref must cite rtc:")
        if self.source_mel_ref is not None and not self.source_mel_ref.startswith("mel:"):
            raise SignalingValidationError("kar.validation.mel_ref", "source_mel_ref must cite mel:")
        if not (0.0 <= self.magnitude <= 1.0):
            raise SignalingValidationError("kar.validation.magnitude", "magnitude out of range")
        _validate_no_secrets(self.residue_id, self.statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "kar-action-residue",
            "schema_version": KAR_SCHEMA_VERSION,
            "residue_id": self.residue_id,
            "source_rtc_ref": self.source_rtc_ref,
            "source_mel_ref": self.source_mel_ref,
            "residue_class": self.residue_class,
            "magnitude": self.magnitude,
            "evidence_refs": list(self.evidence_refs),
            "statement": self.statement,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "authority_created": False,
            "residue_is_not_permission": True,
            "residue_is_not_punishment": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("kar.validation.secret", "secrets forbidden in residue records")


def classify_residue_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _RESIDUE_AS_PUNISHMENT):
        return "residue_as_punishment"
    if any(p in lower for p in _RESIDUE_AS_PERMISSION):
        return "residue_as_permission"
    if any(p in lower for p in _HISTORY_REWRITE):
        return "history_rewrite"
    return "unknown"


def residue_from_fixture(fixture: dict[str, str]) -> ActionResidueRecord:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    mel = fixture.get("source_mel_ref") or None
    return ActionResidueRecord(
        residue_id=fixture["residue_id"],
        source_rtc_ref=fixture.get("source_rtc_ref", "rtc:event-fixture"),
        source_mel_ref=mel,
        residue_class=fixture.get("residue_class", "action_trace"),  # type: ignore[arg-type]
        magnitude=float(fixture.get("magnitude", "0.4")),
        evidence_refs=evidence,
        statement=fixture.get("statement", "bounded action residue"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-14T00:00:00.000000Z"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "KAR_SCHEMA_VERSION",
    "ActionResidueRecord",
    "classify_residue_risk",
    "residue_from_fixture",
]
