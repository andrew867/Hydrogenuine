"""DSE core types — receipts, admission decisions, rollback records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash


@dataclass(frozen=True)
class SinkAdmissionDecision:
    admitted: bool
    reason_code: str
    sink_class: str
    tranche_id: str
    request_id: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    permission_granted: bool = False
    authority_created: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "reason_code": self.reason_code,
            "sink_class": self.sink_class,
            "tranche_id": self.tranche_id,
            "request_id": self.request_id,
            "operator_ref": self.operator_ref,
            "evidence_admissible": self.evidence_admissible,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
        }


@dataclass
class DurableSinkReceipt:
    receipt_id: str
    sink_class: str
    tranche_id: str
    request_id: str
    target_ref: str
    content_digest: str
    rollback_marker_ref: str
    durable_write_performed: bool = True
    permission_granted: bool = False
    authority_created: bool = False
    observed_at: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def receipt_hash(self) -> str:
        payload = {
            "receipt_id": self.receipt_id,
            "sink_class": self.sink_class,
            "tranche_id": self.tranche_id,
            "request_id": self.request_id,
            "target_ref": self.target_ref,
            "content_digest": self.content_digest,
            "rollback_marker_ref": self.rollback_marker_ref,
            "durable_write_performed": self.durable_write_performed,
            "observed_at": self.observed_at,
        }
        return compute_record_hash(payload)

    def to_payload(self) -> dict[str, Any]:
        body = {
            "receipt_id": self.receipt_id,
            "sink_class": self.sink_class,
            "tranche_id": self.tranche_id,
            "request_id": self.request_id,
            "target_ref": self.target_ref,
            "content_digest": self.content_digest,
            "rollback_marker_ref": self.rollback_marker_ref,
            "durable_write_performed": self.durable_write_performed,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
            "observed_at": self.observed_at,
            "receipt_hash": self.receipt_hash(),
            **self.extra,
        }
        return body


@dataclass
class SinkRollbackRecord:
    rollback_id: str
    receipt_id: str
    tranche_id: str
    target_ref: str
    rollback_digest: str
    compensatable: bool = True
    observed_at: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "receipt_id": self.receipt_id,
            "tranche_id": self.tranche_id,
            "target_ref": self.target_ref,
            "rollback_digest": self.rollback_digest,
            "compensatable": self.compensatable,
            "observed_at": self.observed_at,
            "record_hash": compute_record_hash(
                {
                    "rollback_id": self.rollback_id,
                    "receipt_id": self.receipt_id,
                    "target_ref": self.target_ref,
                    "rollback_digest": self.rollback_digest,
                }
            ),
        }


__all__ = ["DurableSinkReceipt", "SinkAdmissionDecision", "SinkRollbackRecord"]
