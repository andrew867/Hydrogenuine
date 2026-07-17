"""SYN provenance records — evidence only, not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

SYN_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ProvenanceRecord:
    provenance_id: str
    artifact_id: str
    generator_module: str
    generation_method: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "syn-provenance-record",
            "schema_version": SYN_SCHEMA_VERSION,
            "provenance_id": self.provenance_id,
            "artifact_id": self.artifact_id,
            "generator_module": self.generator_module,
            "generation_method": self.generation_method,
            "created_at": self.created_at,
            "provenance_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class WatermarkMetadata:
    watermark_id: str
    artifact_id: str
    metadata_ref: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "syn-watermark-metadata",
            "schema_version": SYN_SCHEMA_VERSION,
            "watermark_id": self.watermark_id,
            "artifact_id": self.artifact_id,
            "metadata_ref": self.metadata_ref,
            "created_at": self.created_at,
            "is_safety_proof": False,
            "watermark_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


__all__ = ["ProvenanceRecord", "WatermarkMetadata"]
