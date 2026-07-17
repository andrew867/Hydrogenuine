"""RES typed schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

RES_SCHEMA_VERSION = "1.0"

AcquisitionMode = Literal[
    "offline_docs",
    "provided_files",
    "approved_web_search",
    "approved_api",
    "operator_supplied",
    "forbidden",
    "unknown",
]

SourceType = Literal[
    "repo_doc",
    "proof_bundle",
    "uploaded_file",
    "official_source",
    "web_source",
    "operator_statement",
    "generated_summary",
    "unknown",
]

SupportLevel = Literal["direct", "indirect", "inferred", "contradicted", "stale", "unknown"]


@dataclass(frozen=True)
class ResearchRequest:
    request_id: str
    question: str
    purpose: str
    acquisition_mode: AcquisitionMode
    allowed_source_classes: tuple[str, ...]
    forbidden_source_classes: tuple[str, ...]
    freshness_requirement: str
    privacy_sensitivity: str
    uncertainty: str
    created_at: str
    evidence_refs: tuple[str, ...] = ()
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "res-research-request",
            "schema_version": RES_SCHEMA_VERSION,
            "request_id": self.request_id,
            "question": self.question,
            "purpose": self.purpose,
            "acquisition_mode": self.acquisition_mode,
            "allowed_source_classes": list(self.allowed_source_classes),
            "forbidden_source_classes": list(self.forbidden_source_classes),
            "freshness_requirement": self.freshness_requirement,
            "privacy_sensitivity": self.privacy_sensitivity,
            "uncertainty": self.uncertainty,
            "created_at": self.created_at,
            "evidence_refs": list(self.evidence_refs),
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_ref: str
    source_type: SourceType
    claim_supported: str
    support_level: SupportLevel
    created_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_evidence_record(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "res-evidence-record",
            "schema_version": RES_SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "claim_supported": self.claim_supported,
            "support_level": self.support_level,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_request(request: ResearchRequest) -> None:
    if not request.request_id.strip():
        raise RuntimeContextValidationError("res.validation.request_id", "request_id required")
    if request.acquisition_mode in {"approved_web_search", "approved_api"} and "web" in request.forbidden_source_classes:
        raise RuntimeContextValidationError("res.validation.acquisition_mode", "conflicting acquisition/source classes")


def validate_evidence_record(record: EvidenceRecord) -> None:
    if not record.source_ref.strip():
        raise RuntimeContextValidationError("res.validation.source_ref", "source_ref required")
    if not record.source_ref.startswith(("sha256:", "docs/", "workspace/")):
        raise RuntimeContextValidationError("res.validation.source_ref", "source_ref must be hash or repo path ref")
    if "password=" in record.source_ref.lower():
        raise RuntimeContextValidationError("res.validation.source_ref", "secrets forbidden in source refs")


def request_from_fixture(fixture: dict[str, str]) -> ResearchRequest:
    return ResearchRequest(
        request_id=fixture["request_id"],
        question=fixture.get("question", "fixture question"),
        purpose=fixture.get("purpose", "evidence acquisition"),
        acquisition_mode=fixture.get("acquisition_mode", "provided_files"),  # type: ignore[arg-type]
        allowed_source_classes=tuple(fixture.get("allowed_source_classes", "repo_doc|proof_bundle").split("|")),
        forbidden_source_classes=tuple(fixture.get("forbidden_source_classes", "web_source").split("|")),
        freshness_requirement=fixture.get("freshness_requirement", "tim-bound"),
        privacy_sensitivity=fixture.get("privacy_sensitivity", "low"),
        uncertainty=fixture.get("uncertainty", "unknown until supported"),
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        evidence_refs=tuple(fixture.get("evidence_refs", "").split("|")) if fixture.get("evidence_refs") else (),
    )


__all__ = [
    "AcquisitionMode",
    "EvidenceRecord",
    "RES_SCHEMA_VERSION",
    "ResearchRequest",
    "SourceType",
    "SupportLevel",
    "request_from_fixture",
    "validate_evidence_record",
    "validate_request",
]
