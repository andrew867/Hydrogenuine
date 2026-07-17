"""SYN export receipts — append-only, not publication permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

SYN_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ExportReceipt:
    receipt_id: str
    artifact_id: str
    artifact_hash: str
    label_hash: str
    disclosed: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "syn-export-receipt",
            "schema_version": SYN_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "artifact_id": self.artifact_id,
            "artifact_hash": self.artifact_hash,
            "label_hash": self.label_hash,
            "disclosed": self.disclosed,
            "created_at": self.created_at,
            "export_is_not_permission": True,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


__all__ = ["ExportReceipt"]
