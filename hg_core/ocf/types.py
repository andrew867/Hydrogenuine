"""OCF core types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash


class OrganPostureState(str, Enum):
    BRIGHT = "BRIGHT"
    DARK = "DARK"
    DAMPED = "DAMPED"
    PROBE_ONLY = "PROBE_ONLY"
    DECOUPLED = "DECOUPLED"
    RECOVERY = "RECOVERY"
    PANIC_DARK = "PANIC_DARK"
    OFFLINE = "OFFLINE"
    QUARANTINED = "QUARANTINED"
    UNKNOWN = "UNKNOWN"


VALID_POSTURES = frozenset(s for s in OrganPostureState if s != OrganPostureState.UNKNOWN)


@dataclass(frozen=True)
class ControlFieldSource:
    source_id: str
    source_kind: str = "operator_advisory"

    def to_payload(self) -> dict[str, str]:
        return {"source_id": self.source_id, "source_kind": self.source_kind}


@dataclass(frozen=True)
class ControlFieldTarget:
    organ_id: str
    bus_id: str | None = None

    def to_payload(self) -> dict[str, str | None]:
        return {"organ_id": self.organ_id, "bus_id": self.bus_id}


@dataclass(frozen=True)
class ControlFieldIntensity:
    level: float
    unit: str = "normalized"

    def to_payload(self) -> dict[str, object]:
        return {"level": self.level, "unit": self.unit}


@dataclass(frozen=True)
class ControlFieldDuration:
    seconds: float | None = None
    until_observed_at: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {"seconds": self.seconds, "until_observed_at": self.until_observed_at}


@dataclass(frozen=True)
class ControlFieldReason:
    reason_code: str
    detail: str = ""

    def to_payload(self) -> dict[str, str]:
        return {"reason_code": self.reason_code, "detail": self.detail}


@dataclass
class ControlFieldSidebandReceipt:
    receipt_id: str
    field_id: str
    target_organ: str
    posture_from: str
    posture_to: str
    observed_at: str

    def receipt_hash(self) -> str:
        return compute_record_hash(
            {
                "receipt_id": self.receipt_id,
                "field_id": self.field_id,
                "target_organ": self.target_organ,
                "posture_from": self.posture_from,
                "posture_to": self.posture_to,
                "observed_at": self.observed_at,
            }
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "field_id": self.field_id,
            "target_organ": self.target_organ,
            "posture_from": self.posture_from,
            "posture_to": self.posture_to,
            "observed_at": self.observed_at,
            "receipt_hash": self.receipt_hash(),
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class OrganControlField:
    field_id: str
    source: ControlFieldSource
    target: ControlFieldTarget
    intensity: ControlFieldIntensity
    duration: ControlFieldDuration
    reason: ControlFieldReason
    requested_posture: OrganPostureState
    restrict_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "source": self.source.to_payload(),
            "target": self.target.to_payload(),
            "intensity": self.intensity.to_payload(),
            "duration": self.duration.to_payload(),
            "reason": self.reason.to_payload(),
            "requested_posture": self.requested_posture.value,
            "restrict_only": self.restrict_only,
            "permission_granted": False,
        }


@dataclass
class PostureTransition:
    transition_id: str
    organ_id: str
    from_posture: OrganPostureState
    to_posture: OrganPostureState
    observed_at: str
    sideband_receipt: ControlFieldSidebandReceipt

    def to_payload(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "organ_id": self.organ_id,
            "from_posture": self.from_posture.value,
            "to_posture": self.to_posture.value,
            "observed_at": self.observed_at,
            "sideband_receipt": self.sideband_receipt.to_payload(),
            "permission_granted": False,
        }


@dataclass
class PostureTransitionRefusal:
    reason_code: str
    organ_id: str
    requested_posture: str

    def to_payload(self) -> dict[str, str]:
        return {
            "reason_code": self.reason_code,
            "organ_id": self.organ_id,
            "requested_posture": self.requested_posture,
        }


@dataclass
class DecouplingPlan:
    plan_id: str
    organ_id: str
    buses_to_isolate: tuple[str, ...]
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "organ_id": self.organ_id, "buses_to_isolate": list(self.buses_to_isolate), "observed_at": self.observed_at}


@dataclass
class RecouplingPlan:
    plan_id: str
    organ_id: str
    audit_ref: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "organ_id": self.organ_id, "audit_ref": self.audit_ref, "observed_at": self.observed_at}


@dataclass
class ProbeRequest:
    request_id: str
    organ_id: str
    diagnostic_kind: str
    observed_at: str

    def to_payload(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "organ_id": self.organ_id,
            "diagnostic_kind": self.diagnostic_kind,
            "observed_at": self.observed_at,
        }


@dataclass
class ProbeResponse:
    request_id: str
    organ_id: str
    status: str
    observed_at: str

    def to_payload(self) -> dict[str, str]:
        return {"request_id": self.request_id, "organ_id": self.organ_id, "status": self.status, "observed_at": self.observed_at}


@dataclass
class PanicDarkReceipt:
    receipt_id: str
    organ_id: str
    observed_at: str
    restrict_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "organ_id": self.organ_id,
            "observed_at": self.observed_at,
            "restrict_only": self.restrict_only,
            "permission_granted": False,
        }


@dataclass
class OCFDecision:
    status: str
    reason_code: str
    permission_granted: bool = False
    authority_created: bool = False
    transition: PostureTransition | None = None
    refusal: PostureTransitionRefusal | None = None
    sideband_receipt: ControlFieldSidebandReceipt | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "status": self.status,
            "reason_code": self.reason_code,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
            "advisory_only": True,
        }
        if self.transition:
            body["transition"] = self.transition.to_payload()
        if self.refusal:
            body["refusal"] = self.refusal.to_payload()
        if self.sideband_receipt:
            body["sideband_receipt"] = self.sideband_receipt.to_payload()
        body.update(self.extra)
        return body


OCFRefusalReason = str

__all__ = [
    "ControlFieldDuration",
    "ControlFieldIntensity",
    "ControlFieldReason",
    "ControlFieldSidebandReceipt",
    "ControlFieldSource",
    "ControlFieldTarget",
    "DecouplingPlan",
    "OCFDecision",
    "OCFRefusalReason",
    "OrganControlField",
    "OrganPostureState",
    "PanicDarkReceipt",
    "PostureTransition",
    "PostureTransitionRefusal",
    "ProbeRequest",
    "ProbeResponse",
    "RecouplingPlan",
    "VALID_POSTURES",
]
