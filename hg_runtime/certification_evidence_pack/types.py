"""CRT typed schemas — claims cannot be green without evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence

from hg_core.policy_safety.errors import PolicyValidationError, REFUSED_CLAIM_WITHOUT_EVIDENCE, REFUSED_FAKE_GREEN
from hg_core.policy_safety.hashing import compute_record_hash

CRT_SCHEMA_VERSION = "1.0"

ClaimStatus = Literal["supported", "unsupported", "stale", "excepted"]

ControlDomain = Literal[
    "authority",
    "identity",
    "secrets",
    "logging",
    "testing",
    "replay",
    "human_oversight",
    "automation_limits",
    "external_actuation",
    "content_provenance",
    "vulnerable_users",
    "cyber_capability",
    "incident_response",
    "retention",
    "transparency",
    "unknown",
]


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    path: str
    content_hash: str
    fresh: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_evidence_ref(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "crt-evidence-reference",
            "schema_version": CRT_SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "path": self.path,
            "content_hash": self.content_hash,
            "fresh": self.fresh,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SafetyClaim:
    claim_id: str
    statement: str
    control_domain: ControlDomain
    status: ClaimStatus
    evidence_refs: tuple[str, ...]
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_claim(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "crt-safety-claim",
            "schema_version": CRT_SCHEMA_VERSION,
            "claim_id": self.claim_id,
            "statement": self.statement,
            "control_domain": self.control_domain,
            "status": self.status,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ExceptionRecord:
    exception_id: str
    detail: str
    control_domain: ControlDomain
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "crt-exception-record",
            "schema_version": CRT_SCHEMA_VERSION,
            "exception_id": self.exception_id,
            "detail": self.detail,
            "control_domain": self.control_domain,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class CertificationSnapshot:
    snapshot_id: str
    branch: str
    head: str
    claims: tuple[SafetyClaim, ...]
    exceptions: tuple[ExceptionRecord, ...]
    evidence_refs: tuple[EvidenceReference, ...]
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "crt-certification-snapshot",
            "schema_version": CRT_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "branch": self.branch,
            "head": self.head,
            "claims": [c.to_payload(include_hash=False) for c in self.claims],
            "exceptions": [e.to_payload(include_hash=False) for e in self.exceptions],
            "evidence_refs": [r.to_payload(include_hash=False) for r in self.evidence_refs],
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AuditorExportBundle:
    export_id: str
    snapshot: CertificationSnapshot
    bundle_hash: str
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "crt-auditor-export-bundle",
            "schema_version": CRT_SCHEMA_VERSION,
            "export_id": self.export_id,
            "snapshot": self.snapshot.to_payload(include_hash=False),
            "bundle_hash": self.bundle_hash,
            "created_at": self.created_at,
            "advisory_only": True,
            "permission_granted": False,
            "certification_granted": False,
        }


def validate_evidence_ref(ref: EvidenceReference) -> None:
    if not ref.evidence_id.strip():
        raise PolicyValidationError("crt.validation.evidence_id", "evidence_id required")
    if not ref.content_hash.startswith("sha256:"):
        raise PolicyValidationError("crt.validation.content_hash", "content_hash must be sha256-pinned")


def validate_claim(claim: SafetyClaim) -> None:
    if not claim.claim_id.strip():
        raise PolicyValidationError("crt.validation.claim_id", "claim_id required")
    if claim.status == "supported" and not claim.evidence_refs:
        raise PolicyValidationError(
            REFUSED_CLAIM_WITHOUT_EVIDENCE,
            "supported claim requires evidence refs",
        )
    if claim.status == "supported" and any(not ref.strip() for ref in claim.evidence_refs):
        raise PolicyValidationError(REFUSED_FAKE_GREEN, "supported claim cannot have empty evidence ref")


def make_claim(
    *,
    claim_id: str,
    statement: str,
    control_domain: ControlDomain,
    status: ClaimStatus,
    evidence_refs: Sequence[str],
    created_at: str,
) -> SafetyClaim:
    """Construct claim with fake-green prevention at schema level."""
    if status == "supported" and not evidence_refs:
        raise PolicyValidationError(REFUSED_FAKE_GREEN, "cannot construct supported claim without evidence")
    return SafetyClaim(
        claim_id=claim_id,
        statement=statement,
        control_domain=control_domain,
        status=status,
        evidence_refs=tuple(evidence_refs),
        created_at=created_at,
    )


__all__ = [
    "AuditorExportBundle",
    "CRT_SCHEMA_VERSION",
    "CertificationSnapshot",
    "ClaimStatus",
    "ControlDomain",
    "EvidenceReference",
    "ExceptionRecord",
    "SafetyClaim",
    "make_claim",
    "validate_claim",
    "validate_evidence_ref",
]
