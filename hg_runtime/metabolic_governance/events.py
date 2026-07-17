"""MET planned RTC event selection helpers."""

from __future__ import annotations

from hg_core.met_cluster.events import planned_met_event_refs

_ADVERSARIAL_EVENTS: dict[str, str] = {
    "growth_as_grant": "MET_AUTHORITY_CONVERSION_REFUSED",
    "waste_as_deletion": "MET_AUTHORITY_CONVERSION_REFUSED",
    "tool_retirement_as_removal": "MET_AUTHORITY_CONVERSION_REFUSED",
    "decommissioning_as_resurrection": "MET_AUTHORITY_CONVERSION_REFUSED",
    "authority_conversion": "MET_AUTHORITY_CONVERSION_REFUSED",
    "naked_scalar": "MET_FAILED_CLOSED",
    "missing_organ": "MET_FAILED_CLOSED",
    "stale_input": "MET_FAILED_CLOSED",
    "forbidden_claim": "MET_AUTHORITY_CONVERSION_REFUSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "MET_AUTHORITY_CONVERSION_REFUSED")


def proposal_event_for_kind(signal_kind: str) -> str:
    mapping = {
        "growth_request": "MET_GROWTH_REQUESTED",
        "disposal_proposal": "MET_DISPOSAL_PROPOSED",
        "tool_retirement_proposal": "MET_TOOL_RETIREMENT_PROPOSED",
        "intake_request": "MET_INTAKE_REQUESTED",
        "digestion_proposal": "MET_DIGESTION_PROPOSED",
        "waste_identified": "MET_WASTE_IDENTIFIED",
        "decommissioning_record": "MET_DECOMMISSIONING_RECORDED",
        "energy_state": "MET_ENERGY_STATE_OBSERVED",
    }
    return mapping.get(signal_kind, "MET_ENERGY_STATE_OBSERVED")


__all__ = [
    "adversarial_selection_event",
    "planned_met_event_refs",
    "proposal_event_for_kind",
]
