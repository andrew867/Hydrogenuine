"""DRB planned RTC event selection helpers."""

from __future__ import annotations

from hg_core.drb_cluster.events import planned_drb_event_refs
from hg_runtime.dream_reflection_boundary.types import ConsolidationDecisionClass

_DECISION_EVENTS: dict[ConsolidationDecisionClass, str] = {
    "discard": "DRB_CONSOLIDATION_DECISION_RECORDED",
    "retain_fragment_only": "DRB_DREAM_FRAGMENT_CREATED",
    "route_lessons": "DRB_DREAM_FRAGMENT_CREATED",
    "route_risk_hint": "DRB_DREAM_FRAGMENT_CREATED",
    "route_obligation_hint": "DRB_DREAM_FRAGMENT_CREATED",
    "route_residue": "DRB_DREAM_FRAGMENT_CREATED",
    "require_operator_review": "DRB_CONSOLIDATION_DECISION_RECORDED",
    "fail_closed": "DRB_UNKNOWN_REFLECTION_FAILED_CLOSED",
    "unknown_fail_closed": "DRB_UNKNOWN_REFLECTION_FAILED_CLOSED",
}

_ADVERSARIAL_EVENTS: dict[str, str] = {
    "scenario_as_history": "DRB_SCENARIO_AS_HISTORY_REFUSED",
    "fragment_as_memory": "DRB_FRAGMENT_AS_MEMORY_REFUSED",
    "simulation_as_proof": "DRB_SIMULATION_AS_PROOF_REFUSED",
    "better_outcome_as_revision": "DRB_BETTER_OUTCOME_AS_REVISION_REFUSED",
    "fragment_as_authority": "DRB_FRAGMENT_AS_AUTHORITY_REFUSED",
    "simulated_operator_approval": "DRB_FRAGMENT_AS_AUTHORITY_REFUSED",
    "simulated_consent": "DRB_FRAGMENT_AS_AUTHORITY_REFUSED",
    "emotional_relief_as_correctness": "DRB_SIMULATION_AS_PROOF_REFUSED",
    "full_episode_memory": "DRB_FRAGMENT_AS_MEMORY_REFUSED",
    "memory_history_mutation": "DRB_FRAGMENT_AS_MEMORY_REFUSED",
    "authority_conversion": "DRB_AUTHORITY_CONVERSION_CONTAINED",
}


def decision_selection_event(decision: ConsolidationDecisionClass) -> str:
    return _DECISION_EVENTS.get(decision, "DRB_UNKNOWN_REFLECTION_FAILED_CLOSED")


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "DRB_SIGNAL_REFUSED")


__all__ = [
    "adversarial_selection_event",
    "decision_selection_event",
    "planned_drb_event_refs",
]
