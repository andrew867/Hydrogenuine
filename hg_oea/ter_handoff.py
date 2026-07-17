"""TER handoff — the admission→dispatch bridge record (UEAK/OEA Slice 2).

"TER handoff" is the bridge named in UEAK_IMPLEMENTATION_PLAN.md Slice 2: an
immutable, canonically-hashed record created after (and only after) a successful
UEAK admission, binding the admission receipt hash and permit identity to exactly
one requested effect, one bounded sink, and one dispatch mode. The handoff confers
NO authority (the non-authority flags live inside the hashed payload, so stripping
them breaks the hash) and performs NO effect — it only translates and records.

Dispatch modes: dry_run | fake_sink | sandbox | blocked. The mode "real_external"
exists in the enum for honest labelling of the future operator-gated tranche but
this builder refuses to create such a handoff — real external dispatch stays
disabled. This module does no filesystem writes, no network access, and spawns
no child processes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from hg_core.governance.canonical_hash import canonical_hash
from hg_oea.registry import lookup_capability
from hg_oea.types import CapabilityDefinition

TER_HANDOFF_SCHEMA = "ueak-ter-handoff"
TER_HANDOFF_SCHEMA_VERSION = "1.0"

DISPATCH_MODES = ("dry_run", "fake_sink", "sandbox", "blocked", "real_external")
BOUNDED_MODES = ("dry_run", "fake_sink", "sandbox")


class TERHandoffError(ValueError):
    """Fail-closed refusal to construct a handoff."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SafetyTranslation:
    allowed: bool
    reason_code: str
    policy_version: str
    risk_class: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "policy_version": self.policy_version,
            "risk_class": self.risk_class,
        }


@dataclass(frozen=True)
class TERHandoff:
    handoff_id: str
    created_at: str
    request_id: str
    permit_id: str
    permit_hash: str
    ueak_receipt_id: str
    ueak_receipt_hash: str
    ueak_dispatch_id: str
    capability_id: str
    effect_class: str
    input_hash: str
    sink_type: str
    dispatch_mode: str
    translation: SafetyTranslation
    # Non-authority discipline (hashed): the handoff itself grants nothing.
    authority_created: bool = False
    permission_granted: bool = False
    live_action_performed: bool = False
    no_external_effects: bool = True
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "record_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": TER_HANDOFF_SCHEMA,
            "schema_version": TER_HANDOFF_SCHEMA_VERSION,
            "handoff_id": self.handoff_id,
            "created_at": self.created_at,
            "request_id": self.request_id,
            "permit_id": self.permit_id,
            "permit_hash": self.permit_hash,
            "ueak_receipt_id": self.ueak_receipt_id,
            "ueak_receipt_hash": self.ueak_receipt_hash,
            "ueak_dispatch_id": self.ueak_dispatch_id,
            "capability_id": self.capability_id,
            "effect_class": self.effect_class,
            "input_hash": self.input_hash,
            "sink_type": self.sink_type,
            "dispatch_mode": self.dispatch_mode,
            "translation": self.translation.to_payload(),
            "authority_created": self.authority_created,
            "permission_granted": self.permission_granted,
            "live_action_performed": self.live_action_performed,
            "no_external_effects": self.no_external_effects,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    def verify_hash(self) -> bool:
        return self.record_hash == canonical_hash(self.to_payload(include_hash=False))


def create_ter_handoff(
    *,
    admission_receipt: Any,
    dispatch_plan: Any,
    proposed_action: Mapping[str, Any],
    dispatch_mode: str,
    sink_type: str,
    created_at: str,
    capability: CapabilityDefinition | None = None,
) -> TERHandoff:
    """Build a handoff from a REAL admitted UEAK receipt + dispatch plan.

    Fail-closed rules:
    - refused/missing admission → no handoff (refused receipts carry
      dispatch_id=None, so the structural check also catches them);
    - missing permit binding → no handoff;
    - dispatch_mode "real_external" → refused here, always;
    - unknown dispatch_mode / capability mismatch → refused.
    """
    if admission_receipt is None:
        raise TERHandoffError("missing_admission")
    if getattr(admission_receipt, "status", "") != "admitted":
        raise TERHandoffError("admission_not_admitted")
    receipt_hash = getattr(admission_receipt, "receipt_hash", "")
    dispatch_id = getattr(admission_receipt, "dispatch_id", None)
    if not receipt_hash or not dispatch_id:
        raise TERHandoffError("missing_admission")
    if dispatch_plan is None:
        raise TERHandoffError("missing_dispatch_plan")
    permit_binding = getattr(dispatch_plan, "permit_binding", None)
    permit_id = getattr(permit_binding, "permit_id", "") if permit_binding else ""
    permit_hash = getattr(permit_binding, "permit_hash", "") if permit_binding else ""
    if not permit_id or not permit_hash:
        raise TERHandoffError("missing_permit")
    if dispatch_mode == "real_external":
        raise TERHandoffError("real_external_dispatch_disabled_by_default")
    if dispatch_mode not in BOUNDED_MODES and dispatch_mode != "blocked":
        raise TERHandoffError("unknown_dispatch_mode")

    capability_id = getattr(dispatch_plan, "capability_id", "")
    cap = capability or lookup_capability(capability_id)
    if cap is None:
        translation = SafetyTranslation(
            allowed=False, reason_code="unknown_capability",
            policy_version=TER_HANDOFF_SCHEMA_VERSION, risk_class="unknown")
        effective_mode = "blocked"
    elif dispatch_mode == "blocked":
        translation = SafetyTranslation(
            allowed=False, reason_code="mode_blocked",
            policy_version=TER_HANDOFF_SCHEMA_VERSION, risk_class=cap.risk_class)
        effective_mode = "blocked"
    else:
        translation = SafetyTranslation(
            allowed=True, reason_code="bounded_mode_ok",
            policy_version=TER_HANDOFF_SCHEMA_VERSION, risk_class=cap.risk_class)
        effective_mode = dispatch_mode

    input_hash = canonical_hash(dict(proposed_action))
    return TERHandoff(
        handoff_id=f"ter-handoff-{input_hash[7:19]}",
        created_at=created_at,
        request_id=getattr(admission_receipt, "request_id", ""),
        permit_id=permit_id,
        permit_hash=permit_hash,
        ueak_receipt_id=getattr(admission_receipt, "receipt_id", ""),
        ueak_receipt_hash=receipt_hash,
        ueak_dispatch_id=str(dispatch_id),
        capability_id=capability_id,
        effect_class=getattr(dispatch_plan, "effect_class", ""),
        input_hash=input_hash,
        sink_type=sink_type,
        dispatch_mode=effective_mode,
        translation=translation,
    )


__all__ = [
    "BOUNDED_MODES",
    "DISPATCH_MODES",
    "SafetyTranslation",
    "TERHandoff",
    "TERHandoffError",
    "TER_HANDOFF_SCHEMA",
    "TER_HANDOFF_SCHEMA_VERSION",
    "create_ter_handoff",
]
