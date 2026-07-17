"""IMB cluster validation errors — mediation is not authority."""

from __future__ import annotations

REFUSED_IMB_AS_AUTHORITY = "imb.refused.mediation_as_authority"
REFUSED_CONSENSUS_AS_AUTHORITY = "imb.refused.consensus_as_authority"
REFUSED_FORBIDDEN_CLAIM = "imb.refused.forbidden_claim"
IMB_AUTHORITY_CONVERSION_CONTAINED = "imb.contained.authority_conversion"
IMB_CLAIM_RECORDED = "imb.advisory.claim_recorded"
IMB_CONFLICT_DETECTED = "imb.advisory.conflict_detected"
IMB_MEDIATION_RECORDED = "imb.advisory.mediation_recorded"
IMB_FAIL_CLOSED_SELECTED = "imb.advisory.fail_closed_selected"
IMB_UNKNOWN_CONFLICT_FAILED_CLOSED = "imb.refused.unknown_conflict"
IMB_SIGNAL_REFUSED = "imb.refused.signal"
REFUSED_STALE_MEDIATION_POLICY = "imb.refused.stale_mediation_policy"


class ImbValidationError(ValueError):
    """Raised when IMB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "IMB_AUTHORITY_CONVERSION_CONTAINED",
    "IMB_CLAIM_RECORDED",
    "IMB_CONFLICT_DETECTED",
    "IMB_FAIL_CLOSED_SELECTED",
    "IMB_MEDIATION_RECORDED",
    "IMB_SIGNAL_REFUSED",
    "IMB_UNKNOWN_CONFLICT_FAILED_CLOSED",
    "ImbValidationError",
    "REFUSED_CONSENSUS_AS_AUTHORITY",
    "REFUSED_FORBIDDEN_CLAIM",
    "REFUSED_IMB_AS_AUTHORITY",
    "REFUSED_STALE_MEDIATION_POLICY",
]
