"""H8 planned RTC event selection helpers."""

from __future__ import annotations

from hg_core.h8_cluster.events import planned_h8_event_refs

_ADVERSARIAL_EVENTS: dict[str, str] = {
    "drb_as_permission": "H8_DRB_FRAGMENT_AS_PERMISSION_REFUSED",
    "drb_as_memory": "H8_DRB_FRAGMENT_AS_PERMISSION_REFUSED",
    "tep_as_authority": "H8_TEP_ENVELOPE_AS_AUTHORITY_REFUSED",
    "a0_hm_as_authority": "H8_A0_HM_POSTURE_AS_AUTHORITY_REFUSED",
    "boundary_chain_authority": "H8_BOUNDARY_CHAIN_AUTHORITY_REFUSED",
    "authority_conversion": "H8_AUTHORITY_CONVERSION_CONTAINED",
    "naked_scalar": "H8_NAKED_SCALAR_REFUSED",
    "missing_organ": "H8_MISSING_ORGAN_FAILED_CLOSED",
    "stale_approval": "H8_STALE_APPROVAL_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "H8_AUTHORITY_CONVERSION_CONTAINED")


def conflict_route_event(target: str) -> str:
    return "H8_CONFLICT_ROUTED"


__all__ = [
    "adversarial_selection_event",
    "conflict_route_event",
    "planned_h8_event_refs",
]
