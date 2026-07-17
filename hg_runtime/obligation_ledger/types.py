"""OBL types — obligation is not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

OBL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-13T00:00:00.000000Z"

SourceType = Literal[
    "action",
    "non_action",
    "residue",
    "incident",
    "publication",
    "external_effect",
    "operator_commitment",
    "system_commitment",
    "unknown",
]
ObligationType = Literal[
    "preserve_evidence",
    "disclose",
    "notify_operator",
    "clean_up",
    "compensate",
    "rollback",
    "expire",
    "review",
    "refuse_future",
    "update_docs",
    "unknown",
]
OwedTo = Literal["operator", "runtime", "future_agent", "external_system", "public", "unknown"]
ClosureType = Literal[
    "completed",
    "reclassified",
    "superseded",
    "expired",
    "operator_waived",
    "impossible",
    "unsafe_to_complete",
    "unknown",
]

_OBLIGATION_AS_AUTHORITY = ("obligation grants permission", "owed so proceed", "must act now")
_AUTONOMOUS_CLEANUP = ("autonomous cleanup", "auto clean up", "execute cleanup without review")
_COMPENSATION_BYPASS = ("compensation bypass", "skip compensation review", "waive compensation")


@dataclass(frozen=True)
class ObligationRecord:
    obligation_id: str
    source_ref: str
    source_type: SourceType
    obligation_type: ObligationType
    owed_to: OwedTo
    urgency: str
    due_by: str | None
    evidence_refs: tuple[str, ...]
    statement: str
    created_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise SignalingValidationError("obl.validation.source_ref", "source_ref required")
        _validate_no_secrets(self.obligation_id, self.statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "obl-obligation-record",
            "schema_version": OBL_SCHEMA_VERSION,
            "obligation_id": self.obligation_id,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "obligation_type": self.obligation_type,
            "owed_to": self.owed_to,
            "urgency": self.urgency,
            "due_by": self.due_by,
            "evidence_refs": list(self.evidence_refs),
            "statement": self.statement,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "authority_created": False,
            "obligation_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ObligationClosure:
    closure_id: str
    obligation_ref: str
    closure_type: ClosureType
    evidence_refs: tuple[str, ...]
    closed_by_ref: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.obligation_ref.startswith("obl:"):
            raise SignalingValidationError("obl.validation.obligation_ref", "obligation_ref must cite obl:")
        _validate_no_secrets(self.closure_id, self.closed_by_ref, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "obl-obligation-closure",
            "schema_version": OBL_SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "obligation_ref": self.obligation_ref,
            "closure_type": self.closure_type,
            "evidence_refs": list(self.evidence_refs),
            "closed_by_ref": self.closed_by_ref,
            "authority_created": False,
            "closure_is_not_execution": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("obl.validation.secret", "secrets forbidden in obligation records")


def classify_obligation_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _OBLIGATION_AS_AUTHORITY):
        return "obligation_as_authority"
    if any(p in lower for p in _AUTONOMOUS_CLEANUP):
        return "autonomous_cleanup"
    if any(p in lower for p in _COMPENSATION_BYPASS):
        return "compensation_bypass"
    return "unknown"


def obligation_from_fixture(fixture: dict[str, str]) -> ObligationRecord:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    due = fixture.get("due_by") or None
    return ObligationRecord(
        obligation_id=fixture["obligation_id"],
        source_ref=fixture.get("source_ref", "kar:residue-fixture"),
        source_type=fixture.get("source_type", "residue"),  # type: ignore[arg-type]
        obligation_type=fixture.get("obligation_type", "preserve_evidence"),  # type: ignore[arg-type]
        owed_to=fixture.get("owed_to", "operator"),  # type: ignore[arg-type]
        urgency=fixture.get("urgency", "medium"),
        due_by=due,
        evidence_refs=evidence,
        statement=fixture.get("statement", "bounded obligation fixture"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-14T00:00:00.000000Z"),
    )


def closure_from_fixture(fixture: dict[str, str]) -> ObligationClosure:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return ObligationClosure(
        closure_id=fixture["closure_id"],
        obligation_ref=fixture.get("obligation_ref", "obl:obligation-fixture"),
        closure_type=fixture.get("closure_type", "review"),  # type: ignore[arg-type]
        evidence_refs=evidence,
        closed_by_ref=fixture.get("closed_by_ref", "operator:fixture"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "OBL_SCHEMA_VERSION",
    "ObligationClosure",
    "ObligationRecord",
    "classify_obligation_risk",
    "closure_from_fixture",
    "obligation_from_fixture",
]
