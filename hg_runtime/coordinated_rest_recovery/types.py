"""CRR integration alignment types — recovery is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.lifecycle.errors import LifecycleValidationError
from hg_core.policy_safety.hashing import compute_record_hash

CRR_ALIGNMENT_SCHEMA_VERSION = "1.0"

SourceModule = Literal["els", "msc", "ysr", "unknown"]


@dataclass(frozen=True)
class RecoveryAlignmentRecord:
    alignment_id: str
    source_module: SourceModule
    recovery_marker_ref: str
    snapshot_hash_ref: str | None
    recovery_active: bool
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_alignment_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "crr-recovery-alignment",
            "schema_version": CRR_ALIGNMENT_SCHEMA_VERSION,
            "alignment_id": self.alignment_id,
            "source_module": self.source_module,
            "recovery_marker_ref": self.recovery_marker_ref,
            "snapshot_hash_ref": self.snapshot_hash_ref,
            "recovery_active": self.recovery_active,
            "created_at": self.created_at,
            "expiry": self.expiry,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_alignment_fields(record: RecoveryAlignmentRecord) -> None:
    if not record.alignment_id.strip():
        raise LifecycleValidationError("crr.validation.alignment_id", "alignment_id required")
    if "password=" in record.recovery_marker_ref.lower():
        raise LifecycleValidationError("crr.validation.secret", "secrets forbidden in recovery refs")
    if record.snapshot_hash_ref and not record.snapshot_hash_ref.startswith("sha256:"):
        raise LifecycleValidationError(
            "crr.validation.snapshot_hash_ref",
            "snapshot_hash_ref must be sha256-pinned when present",
        )


def alignment_from_fixture(fixture: dict[str, str]) -> RecoveryAlignmentRecord:
    return RecoveryAlignmentRecord(
        alignment_id=fixture["alignment_id"],
        source_module=fixture.get("source_module", "els"),  # type: ignore[arg-type]
        recovery_marker_ref=fixture.get("recovery_marker_ref", "crr:fixture-marker"),
        snapshot_hash_ref=fixture.get("snapshot_hash_ref") or None,
        recovery_active=fixture.get("recovery_active", "0") == "1",
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T20:00:00.000000Z"),
    )


__all__ = [
    "CRR_ALIGNMENT_SCHEMA_VERSION",
    "RecoveryAlignmentRecord",
    "SourceModule",
    "alignment_from_fixture",
    "validate_alignment_fields",
]
