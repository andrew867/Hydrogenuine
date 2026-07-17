"""SYN typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.errors import PolicyValidationError
from hg_core.policy_safety.hashing import compute_record_hash

SYN_SCHEMA_VERSION = "1.0"

ContentClass = Literal[
    "text",
    "code",
    "audio",
    "image",
    "video",
    "mixed_media",
    "metadata_only",
    "unknown",
]

RiskClass = Literal[
    "ordinary_generated_content",
    "synthetic_identity_or_voice",
    "deepfake_or_realistic_person_media",
    "public_figure_or_institution_impersonation",
    "misleading_context",
    "undisclosed_generation",
    "unknown",
]


@dataclass(frozen=True)
class SyntheticContentArtifact:
    artifact_id: str
    content_class: ContentClass
    content_ref: str
    generated: bool
    created_at: str
    source_module: str = "fixture"
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_artifact(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "syn-synthetic-content-artifact",
            "schema_version": SYN_SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "content_class": self.content_class,
            "content_ref": self.content_ref,
            "generated": self.generated,
            "created_at": self.created_at,
            "source_module": self.source_module,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ContentDisclosureLabel:
    label_id: str
    artifact_id: str
    disclosure_text: str
    disclosed: bool
    risk_class: RiskClass
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_disclosure_label(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "syn-content-disclosure-label",
            "schema_version": SYN_SCHEMA_VERSION,
            "label_id": self.label_id,
            "artifact_id": self.artifact_id,
            "disclosure_text": self.disclosure_text,
            "disclosed": self.disclosed,
            "risk_class": self.risk_class,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MediaRiskClassification:
    artifact_id: str
    risk_class: RiskClass
    rationale: str
    fail_closed: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "syn-media-risk-classification",
            "schema_version": SYN_SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "risk_class": self.risk_class,
            "rationale": self.rationale,
            "fail_closed": self.fail_closed,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_artifact(artifact: SyntheticContentArtifact) -> None:
    if not artifact.artifact_id.strip():
        raise PolicyValidationError("syn.validation.artifact_id", "artifact_id required")
    if not artifact.content_ref.strip():
        raise PolicyValidationError("syn.validation.content_ref", "content_ref required (hash/ref only)")
    if "://" in artifact.content_ref and not artifact.content_ref.startswith("sha256:"):
        raise PolicyValidationError("syn.validation.content_ref", "content_ref must be hash/ref not URL body")


def validate_disclosure_label(label: ContentDisclosureLabel) -> None:
    if not label.label_id.strip():
        raise PolicyValidationError("syn.validation.label_id", "label_id required")
    if label.disclosed and not label.disclosure_text.strip():
        raise PolicyValidationError("syn.validation.disclosure_text", "disclosed label requires disclosure_text")


__all__ = [
    "ContentClass",
    "ContentDisclosureLabel",
    "MediaRiskClassification",
    "RiskClass",
    "SYN_SCHEMA_VERSION",
    "SyntheticContentArtifact",
    "validate_artifact",
    "validate_disclosure_label",
]
