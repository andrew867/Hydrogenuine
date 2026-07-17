"""H8 cluster validation errors — organism coherence is not authority."""

from __future__ import annotations

REFUSED_H8_AS_AUTHORITY = "h8.refused.organism_as_authority"
REFUSED_MISSING_ORGAN = "h8.refused.missing_organ"
REFUSED_UNKNOWN_ORGAN = "h8.refused.unknown_organ"
REFUSED_STALE_APPROVAL = "h8.refused.stale_approval"
REFUSED_NAKED_SCALAR = "h8.refused.naked_scalar"
REFUSED_DRB_AS_PERMISSION = "h8.refused.drb_fragment_as_permission"
REFUSED_DRB_AS_MEMORY = "h8.refused.drb_fragment_as_memory"
REFUSED_TEP_AS_AUTHORITY = "h8.refused.tep_envelope_as_authority"
REFUSED_A0_HM_AS_AUTHORITY = "h8.refused.a0_hm_posture_as_authority"
REFUSED_BOUNDARY_CHAIN_AUTHORITY = "h8.refused.boundary_chain_launders_authority"
REFUSED_INCOMPLETE_MODULE_RECEIPT = "h8.refused.incomplete_module_receipt"
REFUSED_FORBIDDEN_ORGANISM_CLAIM = "h8.refused.forbidden_organism_claim"
H8_AUTHORITY_CONVERSION_CONTAINED = "h8.contained.authority_conversion"
H8_ORGANISM_STATE_SUMMARY_CREATED = "h8.advisory.organism_state_summary_created"
H8_COHERENCE_RECEIPT_CREATED = "h8.advisory.coherence_receipt_created"
H8_CONFLICT_ROUTED = "h8.advisory.conflict_routed"
H8_ORGANISM_COHERENCE_RECORDED = "h8.advisory.organism_coherence_recorded"
H8_UNKNOWN_ORGANISM_FAILED_CLOSED = "h8.refused.unknown_organism"


class H8ValidationError(ValueError):
    """Raised when H8 records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "H8_AUTHORITY_CONVERSION_CONTAINED",
    "H8_COHERENCE_RECEIPT_CREATED",
    "H8_CONFLICT_ROUTED",
    "H8_ORGANISM_COHERENCE_RECORDED",
    "H8_ORGANISM_STATE_SUMMARY_CREATED",
    "H8_UNKNOWN_ORGANISM_FAILED_CLOSED",
    "H8ValidationError",
    "REFUSED_A0_HM_AS_AUTHORITY",
    "REFUSED_BOUNDARY_CHAIN_AUTHORITY",
    "REFUSED_DRB_AS_MEMORY",
    "REFUSED_DRB_AS_PERMISSION",
    "REFUSED_FORBIDDEN_ORGANISM_CLAIM",
    "REFUSED_H8_AS_AUTHORITY",
    "REFUSED_INCOMPLETE_MODULE_RECEIPT",
    "REFUSED_MISSING_ORGAN",
    "REFUSED_NAKED_SCALAR",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_TEP_AS_AUTHORITY",
    "REFUSED_UNKNOWN_ORGAN",
]
