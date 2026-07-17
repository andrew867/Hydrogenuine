"""MET cluster validation errors — metabolic governance is not authority."""

from __future__ import annotations

REFUSED_MET_AS_AUTHORITY = "met.refused.metabolic_as_authority"
REFUSED_MISSING_ORGAN = "met.refused.missing_organ"
REFUSED_UNKNOWN_ORGAN = "met.refused.unknown_organ"
REFUSED_STALE_INPUT = "met.refused.stale_input"
REFUSED_NAKED_SCALAR = "met.refused.naked_scalar"
REFUSED_GROWTH_AS_GRANT = "met.refused.growth_request_as_grant"
REFUSED_WASTE_AS_DELETION = "met.refused.waste_proposal_as_deletion"
REFUSED_TOOL_RETIREMENT_AS_REMOVAL = "met.refused.tool_retirement_as_removal"
REFUSED_DECOMMISSIONING_AS_RESURRECTION = "met.refused.decommissioning_as_resurrection"
REFUSED_FORBIDDEN_METABOLIC_CLAIM = "met.refused.forbidden_metabolic_claim"
MET_AUTHORITY_CONVERSION_CONTAINED = "met.contained.authority_conversion"
MET_ENERGY_STATE_OBSERVED = "met.advisory.energy_state_observed"
MET_POSTURE_CREATED = "met.advisory.posture_created"
MET_RECEIPT_CREATED = "met.advisory.receipt_created"
MET_ORGAN_ROUTE_CREATED = "met.advisory.organ_route_created"
MET_METABOLIC_SUMMARY_RECORDED = "met.advisory.metabolic_summary_recorded"
MET_FAILED_CLOSED = "met.refused.failed_closed"
MET_GROWTH_REQUESTED = "met.advisory.growth_requested"
MET_DISPOSAL_PROPOSED = "met.advisory.disposal_proposed"
MET_TOOL_RETIREMENT_PROPOSED = "met.advisory.tool_retirement_proposed"


class MetValidationError(ValueError):
    """Raised when MET records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "MET_AUTHORITY_CONVERSION_CONTAINED",
    "MET_DISPOSAL_PROPOSED",
    "MET_ENERGY_STATE_OBSERVED",
    "MET_FAILED_CLOSED",
    "MET_GROWTH_REQUESTED",
    "MET_METABOLIC_SUMMARY_RECORDED",
    "MET_ORGAN_ROUTE_CREATED",
    "MET_POSTURE_CREATED",
    "MET_RECEIPT_CREATED",
    "MET_TOOL_RETIREMENT_PROPOSED",
    "MetValidationError",
    "REFUSED_DECOMMISSIONING_AS_RESURRECTION",
    "REFUSED_FORBIDDEN_METABOLIC_CLAIM",
    "REFUSED_GROWTH_AS_GRANT",
    "REFUSED_MET_AS_AUTHORITY",
    "REFUSED_MISSING_ORGAN",
    "REFUSED_NAKED_SCALAR",
    "REFUSED_STALE_INPUT",
    "REFUSED_TOOL_RETIREMENT_AS_REMOVAL",
    "REFUSED_UNKNOWN_ORGAN",
    "REFUSED_WASTE_AS_DELETION",
]
