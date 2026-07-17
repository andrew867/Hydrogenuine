"""Static capability descriptor registry stub for GPP Phase 1."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_core.governance.types import CapabilityDescriptor, DecisionReference

# Phase 1 fixtures — no live HAL/SOAR registry yet.
CAPABILITY_REGISTRY: dict[str, CapabilityDescriptor] = {
    "cap.oea_stub_log": CapabilityDescriptor(
        capability_id="cap.oea_stub_log",
        effect_class="audit_log",
        description="Phase 0 OEA stub audit log only",
        bind_allowed=True,
    ),
    "cap.memory_write_stub": CapabilityDescriptor(
        capability_id="cap.memory_write_stub",
        effect_class="derived_store",
        description="Derived memory write-back stub",
        bind_allowed=True,
    ),
    "cap.external_post": CapabilityDescriptor(
        capability_id="cap.external_post",
        effect_class="external_write",
        description="External publish — denied in Phase 1 scaffold",
        bind_allowed=False,
    ),
    "cap.external_write_scaffold": CapabilityDescriptor(
        capability_id="cap.external_write_scaffold",
        effect_class="external_write",
        description="Permit-gated external write scaffold for UEAK tests",
        bind_allowed=True,
    ),
    "local_report_file.write": CapabilityDescriptor(
        capability_id="local_report_file.write",
        effect_class="local_report",
        description="Bounded local report file write via OEA",
        bind_allowed=True,
    ),
}

DECISION_FIXTURES: dict[str, DecisionReference] = {
    "dec_allow_stub": DecisionReference(decision_ref="dec_allow_stub", verdict="allow"),
    "dec_hal_accept": DecisionReference(decision_ref="dec_hal_accept", verdict="allow"),
    "dec_hal_reject": DecisionReference(
        decision_ref="dec_hal_reject",
        verdict="deny",
        reason_code="hal_rejected",
    ),
    "dec_hal_no_op": DecisionReference(
        decision_ref="dec_hal_no_op",
        verdict="deny",
        reason_code="hal_no_op",
    ),
    "dec_deny_policy": DecisionReference(
        decision_ref="dec_deny_policy",
        verdict="deny",
        reason_code="policy_denied",
    ),
    "dec_deny_unknown_effect": DecisionReference(
        decision_ref="dec_deny_unknown_effect",
        verdict="deny",
        reason_code="effect_not_permitted",
    ),
}


def lookup_capability(capability_id: str) -> Optional[CapabilityDescriptor]:
    return CAPABILITY_REGISTRY.get(capability_id)


def lookup_decision(decision_ref: str) -> Optional[DecisionReference]:
    return DECISION_FIXTURES.get(decision_ref)


def registry_snapshot() -> Mapping[str, CapabilityDescriptor]:
    return dict(CAPABILITY_REGISTRY)


__all__ = [
    "CAPABILITY_REGISTRY",
    "DECISION_FIXTURES",
    "lookup_capability",
    "lookup_decision",
    "registry_snapshot",
]
