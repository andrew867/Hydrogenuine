"""DRB cluster validation errors — reflection is not authority."""

from __future__ import annotations

REFUSED_DRB_AS_AUTHORITY = "drb.refused.reflection_as_authority"
REFUSED_SCENARIO_AS_HISTORY = "drb.refused.scenario_as_history"
REFUSED_FRAGMENT_AS_MEMORY = "drb.refused.fragment_as_memory"
REFUSED_SIMULATION_AS_PROOF = "drb.refused.simulation_as_proof"
REFUSED_BETTER_OUTCOME_AS_REVISION = "drb.refused.better_outcome_as_revision"
REFUSED_FRAGMENT_AS_AUTHORITY = "drb.refused.fragment_as_authority"
REFUSED_SIMULATED_OPERATOR_APPROVAL = "drb.refused.simulated_operator_approval"
REFUSED_SIMULATED_CONSENT = "drb.refused.simulated_consent"
REFUSED_EMOTIONAL_RELIEF_AS_CORRECTNESS = "drb.refused.emotional_relief_as_correctness"
REFUSED_FULL_EPISODE_MEMORY = "drb.refused.full_episode_memory"
REFUSED_MEMORY_HISTORY_MUTATION = "drb.refused.memory_history_mutation"
REFUSED_FORBIDDEN_REFLECTION_CLAIM = "drb.refused.forbidden_claim"
DRB_AUTHORITY_CONVERSION_CONTAINED = "drb.contained.authority_conversion"
DRB_REFLECTION_REQUEST_RECORDED = "drb.advisory.reflection_request_recorded"
DRB_COUNTERFACTUAL_SCENARIO_CREATED = "drb.advisory.counterfactual_scenario_created"
DRB_DREAM_FRAGMENT_CREATED = "drb.advisory.dream_fragment_created"
DRB_CONSOLIDATION_DECISION_RECORDED = "drb.advisory.consolidation_decision_recorded"
DRB_REFLECTION_RECEIPT_CREATED = "drb.advisory.reflection_receipt_created"
DRB_SIGNAL_REFUSED = "drb.refused.signal"
DRB_UNKNOWN_REFLECTION_FAILED_CLOSED = "drb.refused.unknown_reflection"


class DrbValidationError(ValueError):
    """Raised when DRB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "DRB_AUTHORITY_CONVERSION_CONTAINED",
    "DRB_CONSOLIDATION_DECISION_RECORDED",
    "DRB_COUNTERFACTUAL_SCENARIO_CREATED",
    "DRB_DREAM_FRAGMENT_CREATED",
    "DRB_REFLECTION_RECEIPT_CREATED",
    "DRB_REFLECTION_REQUEST_RECORDED",
    "DRB_SIGNAL_REFUSED",
    "DRB_UNKNOWN_REFLECTION_FAILED_CLOSED",
    "DrbValidationError",
    "REFUSED_BETTER_OUTCOME_AS_REVISION",
    "REFUSED_DRB_AS_AUTHORITY",
    "REFUSED_EMOTIONAL_RELIEF_AS_CORRECTNESS",
    "REFUSED_FORBIDDEN_REFLECTION_CLAIM",
    "REFUSED_FRAGMENT_AS_AUTHORITY",
    "REFUSED_FRAGMENT_AS_MEMORY",
    "REFUSED_FULL_EPISODE_MEMORY",
    "REFUSED_MEMORY_HISTORY_MUTATION",
    "REFUSED_SCENARIO_AS_HISTORY",
    "REFUSED_SIMULATED_CONSENT",
    "REFUSED_SIMULATED_OPERATOR_APPROVAL",
    "REFUSED_SIMULATION_AS_PROOF",
]
