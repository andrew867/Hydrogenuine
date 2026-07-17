"""TRB types — trust is not truth; calibration is not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.control_cluster.errors import ControlValidationError
from hg_core.policy_safety.hashing import compute_record_hash

TRB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

TrustScope = Literal[
    "identity",
    "proof_gate",
    "report",
    "memory",
    "generated_doc",
    "operator_surface",
    "capability",
    "external_source",
    "unknown",
]
RelianceLevel = Literal["none", "low", "bounded", "high", "forbidden", "unknown"]

_TRUST_AS_TRUTH = (
    "trust score is truth",
    "green gate is universal safety",
    "friendly surface is trustworthy",
    "trust is truth",
    "reliance level proves safety",
)
_CALIBRATION_AS_AUTHORITY = (
    "calibration is authority",
    "calibration permits execution",
    "reliance boundary grants permission",
    "trust calibration authorizes",
)


@dataclass(frozen=True)
class TrustCalibration:
    calibration_id: str
    subject_ref: str
    trust_scope: TrustScope
    reliance_level: RelianceLevel
    evidence_refs: tuple[str, ...]
    freshness: str
    known_limits: str
    revocation_conditions: str
    statement: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.calibration_id,
            self.subject_ref,
            self.known_limits,
            self.revocation_conditions,
            self.statement,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "trb-trust-calibration",
            "schema_version": TRB_SCHEMA_VERSION,
            "calibration_id": self.calibration_id,
            "subject_ref": self.subject_ref,
            "trust_scope": self.trust_scope,
            "reliance_level": self.reliance_level,
            "evidence_refs": list(self.evidence_refs),
            "freshness": self.freshness,
            "known_limits": self.known_limits,
            "revocation_conditions": self.revocation_conditions,
            "statement": self.statement,
            "expires_at": self.expires_at,
            "authority_created": False,
            "trust_is_not_truth": True,
            "calibration_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RelianceBoundary:
    boundary_id: str
    calibration_ref: str
    allowed_use: str
    forbidden_use: str
    required_refresh_condition: str
    required_disclosure: str
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.calibration_ref.startswith("trb:"):
            raise ControlValidationError("trb.validation.calibration_ref", "calibration_ref must cite trb:")
        _validate_no_secrets(
            self.boundary_id,
            self.allowed_use,
            self.forbidden_use,
            self.required_refresh_condition,
            self.required_disclosure,
            self.statement,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "trb-reliance-boundary",
            "schema_version": TRB_SCHEMA_VERSION,
            "boundary_id": self.boundary_id,
            "calibration_ref": self.calibration_ref,
            "allowed_use": self.allowed_use,
            "forbidden_use": self.forbidden_use,
            "required_refresh_condition": self.required_refresh_condition,
            "required_disclosure": self.required_disclosure,
            "statement": self.statement,
            "authority_created": False,
            "trust_is_not_truth": True,
            "calibration_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ControlValidationError("trb.validation.secret", "secrets forbidden in trust records")


def classify_trust_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _TRUST_AS_TRUTH):
        return "trust_as_truth"
    if any(p in lower for p in _CALIBRATION_AS_AUTHORITY):
        return "calibration_as_authority"
    return "unknown"


def calibration_from_fixture(fixture: dict[str, str]) -> TrustCalibration:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return TrustCalibration(
        calibration_id=fixture["calibration_id"],
        subject_ref=fixture.get("subject_ref", "subject:fixture"),
        trust_scope=fixture.get("trust_scope", "proof_gate"),  # type: ignore[arg-type]
        reliance_level=fixture.get("reliance_level", "bounded"),  # type: ignore[arg-type]
        evidence_refs=evidence,
        freshness=fixture.get("freshness", FIXTURE_CLOCK),
        known_limits=fixture.get("known_limits", "bounded reliance only"),
        revocation_conditions=fixture.get("revocation_conditions", "operator revocation or stale evidence"),
        statement=fixture.get("statement", "bounded trust calibration"),
        expires_at=fixture.get("expires_at", "2026-06-15T01:00:00.000000Z"),
    )


def reliance_boundary_from_fixture(fixture: dict[str, str]) -> RelianceBoundary:
    return RelianceBoundary(
        boundary_id=fixture["boundary_id"],
        calibration_ref=fixture.get("calibration_ref", "trb:calibration-1"),
        allowed_use=fixture.get("allowed_use", "advisory review only"),
        forbidden_use=fixture.get("forbidden_use", "authority conversion"),
        required_refresh_condition=fixture.get("required_refresh_condition", "stale evidence or scope change"),
        required_disclosure=fixture.get("required_disclosure", "trust is not truth"),
        statement=fixture.get("statement", "bounded reliance boundary"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "TRB_SCHEMA_VERSION",
    "RelianceBoundary",
    "TrustCalibration",
    "TrustScope",
    "RelianceLevel",
    "calibration_from_fixture",
    "classify_trust_risk",
    "reliance_boundary_from_fixture",
]
