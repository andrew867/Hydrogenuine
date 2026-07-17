"""Admission / concurrency types (CT-06 ADM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MutatingKind = Literal[
    "srp_apply",
    "max_auto_run",
    "mel_cycle",
    "oea_effect",
    "ter_command",
    "crr_recovery",
    "panic",
]

AdmissionVerdict = Literal["admitted", "refused", "queued", "preempted"]


@dataclass(frozen=True)
class ApprovalBinding:
    proposal_hash: str
    registry_hash: str
    expires_at: str | None = None


@dataclass(frozen=True)
class AdmissionRequest:
    request_id: str
    kind: MutatingKind
    idempotency_key: str
    operator_id: str | None = None
    sandbox_id: str | None = None
    capability_id: str | None = None
    approval_binding: ApprovalBinding | None = None
    capability_concurrency: int = 1

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "kind": self.kind,
            "idempotency_key": self.idempotency_key,
            "operator_id": self.operator_id,
            "sandbox_id": self.sandbox_id,
            "capability_id": self.capability_id,
            "approval_binding": (
                {
                    "proposal_hash": self.approval_binding.proposal_hash,
                    "registry_hash": self.approval_binding.registry_hash,
                    "expires_at": self.approval_binding.expires_at,
                }
                if self.approval_binding
                else None
            ),
            "capability_concurrency": self.capability_concurrency,
        }


@dataclass(frozen=True)
class AdmissionToken:
    request_id: str
    kind: MutatingKind
    lock_key: str
    idempotency_key: str
    lease_until: float


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    verdict: AdmissionVerdict
    reason_code: str
    token: AdmissionToken | None = None
    duplicate_of: str | None = None
    events: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "verdict": self.verdict,
            "reason_code": self.reason_code,
            "duplicate_of": self.duplicate_of,
            "request_id": self.token.request_id if self.token else None,
        }


@dataclass(frozen=True)
class PreemptionReceipt:
    preemptor: str
    preempted_request_id: str
    preempted_kind: MutatingKind
    reason_code: str = "admission.preempted.operator_cancelled"

    def to_payload(self) -> dict[str, Any]:
        return {
            "preemptor": self.preemptor,
            "preempted_request_id": self.preempted_request_id,
            "preempted_kind": self.preempted_kind,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class DrainReceipt:
    drained: int
    checkpointed: int
    receipt_id: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "drained": self.drained,
            "checkpointed": self.checkpointed,
            "receipt_id": self.receipt_id,
        }


__all__ = [
    "AdmissionDecision",
    "AdmissionRequest",
    "AdmissionToken",
    "AdmissionVerdict",
    "ApprovalBinding",
    "DrainReceipt",
    "MutatingKind",
    "PreemptionReceipt",
]
